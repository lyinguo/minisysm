#pragma once
#include <memory>
#include <stdexcept>

// MySQL advisory locks span processes and service instances. Hold one connection
// from the authoritative duplicate check through the write; release on every exit.
class UserWriteLock {
    Connection* connection;
public:
    explicit UserWriteLock(Connection* value) : connection(value) {
        std::unique_ptr<sql::PreparedStatement> statement(connection->prepareStatement(
            "SELECT GET_LOCK(CONCAT(DATABASE(), ':user-write'), 10)"));
        std::unique_ptr<sql::ResultSet> result(statement->executeQuery());
        if (!result->next() || result->isNull(1) || result->getInt(1) != 1)
            throw std::runtime_error("User write lock unavailable");
    }
    ~UserWriteLock() {
        try {
            std::unique_ptr<sql::PreparedStatement> statement(connection->prepareStatement(
                "SELECT RELEASE_LOCK(CONCAT(DATABASE(), ':user-write'))"));
            std::unique_ptr<sql::ResultSet> result(statement->executeQuery());
        } catch (...) { /* Connection disposal also releases its advisory locks. */ }
    }
    UserWriteLock(const UserWriteLock&) = delete;
    UserWriteLock& operator=(const UserWriteLock&) = delete;

    bool conflicts(const std::string& login, const std::string& phone, const std::string& excludedId) {
        // Use the throwing connector API: a failed read must never mean "available".
        std::unique_ptr<sql::PreparedStatement> statement(connection->prepareStatement(
            "SELECT id FROM `user` WHERE id <> ? AND (`user` = ? OR tel = ?) LIMIT 1"));
        statement->setString(1, excludedId);
        statement->setString(2, login);
        statement->setString(3, phone);
        std::unique_ptr<sql::ResultSet> result(statement->executeQuery());
        return result->next();
    }
};
