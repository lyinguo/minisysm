package com.zeroone.star.basic_information.service;

import com.zeroone.star.project.dto.j6.basic_information.customer_management.CustomerAddDTO;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import javax.validation.Validator;
import java.util.*;

/** One workbook is one transaction: an invalid row never leaves a partial import. */
@Service
public class CustomerImportService {
    private final JdbcTemplate db;
    private final Validator validator;
    public CustomerImportService(JdbcTemplate db, Validator validator) { this.db = db; this.validator = validator; }

    @Transactional(rollbackFor = Exception.class, isolation = org.springframework.transaction.annotation.Isolation.SERIALIZABLE)
    public int importRows(List<CustomerAddDTO> rows) {
        if (rows == null || rows.isEmpty() || rows.size() > 500) throw new IllegalArgumentException("每次导入需要 1 至 500 条客户数据");
        Set<String> numbers = new HashSet<>();
        for (int i = 0; i < rows.size(); i++) {
            CustomerAddDTO row = rows.get(i);
            String prefix = "第 " + (i + 2) + " 行：";
            if (row == null) throw new IllegalArgumentException(prefix + "客户数据不能为空");
            if (row.getNumber() == null || row.getNumber().trim().isEmpty()) throw new IllegalArgumentException(prefix + "客户编号不能为空");
            row.setNumber(row.getNumber().trim());
            String[] shortFields = {row.getName(), row.getPy(), row.getNumber(), row.getFrame(), row.getUser(), row.getCategory(), row.getGrade(), row.getBank()};
            for (String field : shortFields) if (field != null && field.length() > 32) throw new IllegalArgumentException(prefix + "名称、编号、类别、等级和银行名称等字段最长 32 字");
            if ((row.getAccount() != null && row.getAccount().length() > 64) || (row.getTax() != null && row.getTax().length() > 64)) throw new IllegalArgumentException(prefix + "银行账号和纳税号码最长 64 字");
            if (row.getData() != null && row.getData().length() > 256) throw new IllegalArgumentException(prefix + "备注最长 256 字");
            if (row.getContacts() != null) {
                try {
                    if (row.getContacts().length() > 65535 || !new com.fasterxml.jackson.databind.ObjectMapper().readTree(row.getContacts()).isArray()) throw new IllegalArgumentException();
                } catch (Exception e) { throw new IllegalArgumentException(prefix + "联系人必须为有效的数组"); }
            }
            if (!validator.validate(row).isEmpty()) throw new IllegalArgumentException(prefix + validator.validate(row).iterator().next().getMessage());
            if (!numbers.add(row.getNumber())) throw new IllegalArgumentException(prefix + "客户编号在文件内重复：" + row.getNumber());
            if (!db.queryForList("SELECT id FROM customer WHERE number=? FOR UPDATE", row.getNumber()).isEmpty())
                throw new IllegalArgumentException(prefix + "客户编号已存在：" + row.getNumber());
        }
        for (CustomerAddDTO row : rows) {
            db.update("INSERT INTO customer(id,name,py,number,frame,`user`,category,grade,bank,account,tax,data,contacts,balance,more) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,0,'{}')",
                UUID.randomUUID().toString().replace("-", ""), row.getName().trim(), row.getPy(), row.getNumber(),
                row.getFrame(), row.getUser(), row.getCategory(), row.getGrade(), row.getBank(), row.getAccount(), row.getTax(),
                row.getData(), row.getContacts() == null ? "[]" : row.getContacts());
        }
        return rows.size();
    }
}
