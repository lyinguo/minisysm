package com.zeroone.star.project.components.user;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import java.io.IOException;
import java.util.*;

/** Evaluate committed role selections, rather than a possibly stale resource cache. */
public final class DatabaseResourcePermission {
    private static final ObjectMapper JSON = new ObjectMapper();
    private DatabaseResourcePermission() { }

    public static boolean allowed(JdbcTemplate db, String roleId, String resource) {
        if (roleId == null || resource == null) return false;
        // One statement keeps role selections and enabled catalog entries in one DB snapshot.
        List<Map<String,Object>> rows = db.queryForList(
            "SELECT r.root,f.id AS function_id FROM role r JOIN func_perm f ON f.url=? AND f.is_enable='1' WHERE r.id=?",
            resource, roleId);
        if (rows.isEmpty()) return false;
        Set<String> selected = new HashSet<>();
        try {
            JsonNode root = JSON.readTree(Objects.toString(rows.get(0).get("root"), ""));
            if (root == null || !root.isArray()) return false;
            collect(root, selected, 0);
        } catch (IOException | IllegalArgumentException error) {
            return false;
        }
        return rows.stream().anyMatch(row -> selected.contains(Objects.toString(row.get("function_id"), "")));
    }

    private static void collect(JsonNode nodes, Set<String> selected, int depth) {
        if (depth > 64) throw new IllegalArgumentException("Role permission tree is too deep");
        for (JsonNode node : nodes) {
            if (!node.isObject()) continue;
            JsonNode functions = node.get("fun");
            if (functions != null && functions.isArray()) {
                for (JsonNode function : functions) {
                    JsonNode id = function.get("id");
                    if (id != null && id.isValueNode()) selected.add(id.asText());
                }
            }
            JsonNode children = node.get("children");
            if (children != null && children.isArray()) collect(children, selected, depth + 1);
        }
    }
}
