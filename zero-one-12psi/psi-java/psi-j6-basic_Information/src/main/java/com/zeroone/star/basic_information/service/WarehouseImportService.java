package com.zeroone.star.basic_information.service;

import com.zeroone.star.basic_information.entity.Warehouse;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.*;

@Service
public class WarehouseImportService {
    private final JdbcTemplate db;
    public WarehouseImportService(JdbcTemplate db) { this.db = db; }
    @Transactional(rollbackFor = Exception.class, isolation = org.springframework.transaction.annotation.Isolation.SERIALIZABLE)
    public int importRows(List<Warehouse> rows) {
        if (rows == null || rows.isEmpty() || rows.size() > 500) throw new IllegalArgumentException("每次导入需要 1 至 500 条仓库数据");
        Set<String> codes = new HashSet<>();
        for (int i = 0; i < rows.size(); i++) {
            Warehouse row = rows.get(i);
            String prefix = "第 " + (i + 2) + " 行：";
            if (row == null || row.getNumber() == null || row.getName() == null || row.getNumber().trim().isEmpty() || row.getName().trim().isEmpty())
                throw new IllegalArgumentException(prefix + "仓库编号和名称必填");
            row.setNumber(row.getNumber().trim());
            for (String field : Arrays.asList(row.getName(), row.getNumber(), row.getFrame(), row.getContacts(), row.getTel()))
                if (field != null && field.length() > 32) throw new IllegalArgumentException(prefix + "名称、编号、联系人和电话等字段最长 32 字");
            if ((row.getAdd() != null && row.getAdd().length() > 256) || (row.getData() != null && row.getData().length() > 256))
                throw new IllegalArgumentException(prefix + "地址和备注最长 256 字");
            if (!codes.add(row.getNumber())) throw new IllegalArgumentException(prefix + "仓库编号重复");
            if (!db.queryForList("SELECT id FROM warehouse WHERE number=? FOR UPDATE", row.getNumber()).isEmpty()) throw new IllegalArgumentException(prefix + "仓库编号已存在");
        }
        for (Warehouse row : rows) {
            db.update("INSERT INTO warehouse(id,name,number,frame,contacts,tel,`add`,data) VALUES(?,?,?,?,?,?,?,?)",
                UUID.randomUUID().toString().replace("-", ""), row.getName().trim(), row.getNumber(),
                row.getFrame() == null || row.getFrame().trim().isEmpty() ? "0" : row.getFrame(),
                row.getContacts(), row.getTel(), row.getAdd(), row.getData());
        }
        return rows.size();
    }
}
