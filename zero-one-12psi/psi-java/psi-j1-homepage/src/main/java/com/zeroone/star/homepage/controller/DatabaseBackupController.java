package com.zeroone.star.homepage.controller;

import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.components.user.UserHolder;
import com.zeroone.star.project.vo.JsonVO;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;
import javax.sql.DataSource;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.sql.Connection;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.locks.ReentrantLock;

/** Local Docker MySQL backup. The target is derived from the active datasource, never from request parameters. */
@RestController
@RequestMapping("/homepage/system/backup")
public class DatabaseBackupController {
    private final UserHolder users;
    private final JdbcTemplate db;
    private final DataSource source;
    private final ReentrantLock running=new ReentrantLock();
    @Value("${psi.backup.container:mysql8}") private String container;
    public DatabaseBackupController(UserHolder users,JdbcTemplate db,DataSource source) {this.users=users;this.db=db;this.source=source;}

    private void authorize() {
        UserDTO actor;
        try {actor=users.getCurrentUser();}catch(Exception error){throw new ResponseStatusException(HttpStatus.UNAUTHORIZED,"请重新登录");}
        if(actor==null || actor.getId()==null)throw new ResponseStatusException(HttpStatus.UNAUTHORIZED,"请重新登录");
        List<String> roles=db.queryForList("SELECT role FROM `user` WHERE id=?",String.class,actor.getId());
        if(roles.size()!=1 || !"0".equals(roles.get(0)))throw new ResponseStatusException(HttpStatus.FORBIDDEN,"完整数据备份仅限系统管理员");
    }
    private List<String> command(String shell,String database) {
        if(!container.matches("[A-Za-z0-9][A-Za-z0-9_.-]{0,127}"))throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,"备份容器配置无效");
        return Arrays.asList("docker","exec",container,"sh","-c","export MYSQL_PWD=\"${MYSQL_ROOT_PASSWORD}\"; "+shell,"sh",database);
    }
    private void execute(List<String> command,Path output,int seconds) throws IOException,InterruptedException {
        Path errors=Files.createTempFile("minisysm-backup-errors-",".tmp");
        Process process=null;
        try {
            process=new ProcessBuilder(command).redirectOutput(output.toFile()).redirectError(errors.toFile()).start();
            if(!process.waitFor(seconds,TimeUnit.SECONDS)) {
                process.destroyForcibly();process.waitFor(5,TimeUnit.SECONDS);
                throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,"备份处理超时，请稍后重试");
            }
            if(process.exitValue()!=0)throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,"备份工具执行失败，请确认Docker和MySQL容器已启动，并检查备份容器配置");
        } finally {
            if(process!=null && process.isAlive())process.destroyForcibly();
            Files.deleteIfExists(errors);
        }
    }
    private String database() throws Exception {
        try(Connection connection=source.getConnection()) {
            String name=connection.getCatalog();
            if(name==null || !name.matches("[A-Za-z0-9_]{1,64}"))throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,"无法确认当前业务数据库");
            return name;
        }
    }
    private void verifyServer(String database) throws Exception {
        Path result=Files.createTempFile("minisysm-backup-server-",".tmp");
        try {
            execute(command("exec mysql -uroot --batch --skip-column-names --execute='SELECT @@server_uuid' \"$1\"",database),result,15);
            String actual=new String(Files.readAllBytes(result),StandardCharsets.UTF_8).trim();
            String expected=db.queryForObject("SELECT @@server_uuid",String.class);
            if(!actual.equals(expected))throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,"备份容器与当前系统数据库不一致，已拒绝导出");
            Integer unsupported=db.queryForObject("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_type='BASE TABLE' AND engine<>'InnoDB'",Integer.class);
            if(unsupported!=null && unsupported>0)throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,"存在非事务表，不能保证在线一致性备份，请联系管理员安排停机备份");
        } finally {Files.deleteIfExists(result);}
    }
    private Map<String,Object> statusData() throws Exception {
        String database=database();verifyServer(database);
        Map<String,Object> result=new LinkedHashMap<>();result.put("database",database);result.put("format","SQL");
        result.put("tables",db.queryForObject("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_type='BASE TABLE'",Integer.class));
        result.put("scope","当前业务数据库的表结构、数据、视图、触发器、存储过程和事件");
        return result;
    }
    @GetMapping("/status") public JsonVO<Map<String,Object>> status() throws Exception {authorize();return JsonVO.success(statusData());}

    @GetMapping("/download")
    public ResponseEntity<StreamingResponseBody> download() throws Exception {
        authorize();
        if(!running.tryLock())throw new ResponseStatusException(HttpStatus.CONFLICT,"已有备份正在生成，请稍后重试");
        Path backup=null;
        try {
            String database=database();verifyServer(database);
            backup=Files.createTempFile("minisysm-backup-",".sql");
            execute(command("exec mysqldump -uroot --single-transaction --quick --routines --events --triggers --hex-blob --no-tablespaces --set-gtid-purged=OFF --column-statistics=0 --default-character-set=utf8mb4 \"$1\"",database),backup,120);
            if(Files.size(backup)==0)throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,"备份文件为空，请重试");
            MessageDigest digest=MessageDigest.getInstance("SHA-256");
            try(InputStream input=Files.newInputStream(backup)) {byte[] bytes=new byte[65536];int count;while((count=input.read(bytes))!=-1)digest.update(bytes,0,count);}
            StringBuilder hash=new StringBuilder();for(byte value:digest.digest())hash.append(String.format("%02x",value&255));
            Path ready=backup;
            StreamingResponseBody stream=output->{try {Files.copy(ready,output);}finally {Files.deleteIfExists(ready);}};
            ResponseEntity<StreamingResponseBody> response=ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION,"attachment; filename=minisysm-"+LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss"))+".sql")
                .header(HttpHeaders.CACHE_CONTROL,"no-store")
                .header("X-Backup-SHA256",hash.toString())
                .contentLength(Files.size(ready)).contentType(MediaType.APPLICATION_OCTET_STREAM).body(stream);
            backup=null;return response;
        } finally {if(backup!=null)Files.deleteIfExists(backup);running.unlock();}
    }
}
