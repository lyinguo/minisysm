package com.zeroone.star.basic_information.service;

import com.alibaba.excel.EasyExcel;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.zeroone.star.project.vo.j6.basic_information.supplier_management.ImportResultVO;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import java.math.BigDecimal;
import java.util.*;

@Service
public class SupplierWorkbookService {
    private final JdbcTemplate db;
    public SupplierWorkbookService(JdbcTemplate db) { this.db = db; }
    private String cell(Map<Integer,String> row, Map<String,Integer> columns, String name) {
        Integer index = columns.get(name);
        return index == null || row.get(index) == null ? "" : row.get(index).trim();
    }
    @Transactional(rollbackFor = Exception.class, isolation = org.springframework.transaction.annotation.Isolation.SERIALIZABLE)
    public ImportResultVO importFile(MultipartFile file) {
        if (file == null || file.isEmpty() || file.getSize() > 5 * 1024 * 1024) throw new IllegalArgumentException("请选择不超过 5 MiB 的供应商 Excel 文件");
        List<Map<Integer,String>> workbook;
        try { workbook = EasyExcel.read(file.getInputStream()).headRowNumber(0).sheet().doReadSync(); }
        catch (Exception e) { throw new IllegalArgumentException("Excel 无法解析，请重新下载供应商模板"); }
        if (workbook.isEmpty()) throw new IllegalArgumentException("Excel 没有表头");
        Map<String,Integer> columns = new HashMap<>();
        workbook.get(0).forEach((index, name) -> columns.put(name.replace("*", "").trim(), index));
        if (!columns.containsKey("供应商编号") || !columns.containsKey("供应商名称")) throw new IllegalArgumentException("表头不匹配，请使用供应商导入模板");
        List<Object[]> inserts = new ArrayList<>();
        Set<String> codes = new HashSet<>();
        for (int i = 1; i < workbook.size(); i++) {
            Map<Integer,String> row = workbook.get(i);
            if (row.values().stream().allMatch(value -> value == null || value.trim().isEmpty())) continue;
            String prefix = "第 " + (i + 1) + " 行：";
            String code = cell(row, columns, "供应商编号"), name = cell(row, columns, "供应商名称");
            if (code.isEmpty() || name.isEmpty()) throw new IllegalArgumentException(prefix + "供应商编号和名称必填");
            if (code.length() > 32 || name.length() > 32) throw new IllegalArgumentException(prefix + "编号和名称最长 32 字");
            if (!codes.add(code) || !db.queryForList("SELECT id FROM supplier WHERE number=? FOR UPDATE", code).isEmpty()) throw new IllegalArgumentException(prefix + "供应商编号重复或已存在");
            String frame=cell(row, columns, "所属组织"), user=cell(row, columns, "所属用户"), category=cell(row, columns, "供应商类别");
            String rateText=cell(row, columns, "增值税税率");
            BigDecimal rate;
            try { rate=rateText.isEmpty()?BigDecimal.ZERO:new BigDecimal(rateText); }
            catch (Exception e) { throw new IllegalArgumentException(prefix + "税率应填写小数，例如 0.13"); }
            if (rate.signum()<0 || rate.compareTo(BigDecimal.ONE)>0) throw new IllegalArgumentException(prefix + "税率须在 0 到 1 之间");
            String contacts=cell(row, columns, "联系资料");
            try {
                if (contacts.isEmpty()) {
                    Map<String,Object> contact=new LinkedHashMap<>();
                    contact.put("name",cell(row,columns,"联系人")); contact.put("phone",cell(row,columns,"联系电话")); contact.put("address",cell(row,columns,"联系地址")); contact.put("isMain",true);
                    contacts=new ObjectMapper().writeValueAsString(cell(row,columns,"联系人").isEmpty() && cell(row,columns,"联系电话").isEmpty() && cell(row,columns,"联系地址").isEmpty()?Collections.emptyList():Collections.singletonList(contact));
                } else if (!new ObjectMapper().readTree(contacts).isArray()) throw new IllegalArgumentException();
            } catch (Exception e) { throw new IllegalArgumentException(prefix + "联系资料格式不正确"); }
            inserts.add(new Object[]{UUID.randomUUID().toString().replace("-",""),name,code,code,frame.isEmpty()?"0":frame,user.isEmpty()?"admin":user,
                category.isEmpty()?"常规类别":category,rate,cell(row,columns,"开户银行"),cell(row,columns,"银行账号"),cell(row,columns,"纳税号码"),cell(row,columns,"备注"),contacts});
        }
        if (inserts.isEmpty() || inserts.size()>500) throw new IllegalArgumentException("每次导入需要 1 至 500 条供应商数据");
        for (Object[] row : inserts) db.update("INSERT INTO supplier(id,name,py,number,frame,`user`,category,rate,bank,account,tax,data,contacts,balance,more) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,0,'{}')",row);
        ImportResultVO result=new ImportResultVO();
        result.setTotalCount(inserts.size()); result.setSuccessCount(inserts.size()); result.setFailureCount(0); result.setFailureDetails(Collections.emptyList());
        return result;
    }
}
