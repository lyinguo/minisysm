package com.zeroone.star.supportinfo.controller;

import com.zeroone.star.project.vo.JsonVO;
import com.zeroone.star.supportinfo.entity.Annex;
import com.zeroone.star.supportinfo.service.IAnnexService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.http.HttpStatus;

import javax.annotation.Resource;
import javax.imageio.ImageIO;
import javax.imageio.ImageReader;
import javax.imageio.stream.ImageInputStream;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.file.*;
import java.util.*;

/** Actual avatar bytes and attachment identity are stored together, without a remote DFS dependency. */
@RestController
@RequestMapping("/attachment/avatar")
public class AvatarController {
    @Resource private IAnnexService annexService;
    @Resource private TransactionTemplate transactionTemplate;
    @Value("${attachments.local-root:./data/attachments}") private String localRoot;
    private static final long MAX_BYTES = 5L * 1024 * 1024;

    @PostMapping
    public JsonVO<Map<String, String>> upload(@RequestParam("file") MultipartFile file) throws IOException {
        if (file == null || file.isEmpty() || file.getSize() > MAX_BYTES) {
            return JsonVO.create(null, 9999, "请选择不超过5MB的图片");
        }
        byte[] bytes = file.getBytes();
        String extension;
        try (ImageInputStream input = ImageIO.createImageInputStream(new ByteArrayInputStream(bytes))) {
            Iterator<ImageReader> readers = ImageIO.getImageReaders(input);
            if (!readers.hasNext()) return JsonVO.create(null, 9999, "头像必须是有效的PNG或JPEG图片");
            ImageReader reader = readers.next();
            try {
                reader.setInput(input);
                String format = reader.getFormatName().toLowerCase(Locale.ROOT);
                if (!format.equals("png") && !format.equals("jpeg") && !format.equals("jpg"))
                    return JsonVO.create(null, 9999, "头像仅支持PNG或JPEG图片");
                long width = reader.getWidth(0), height = reader.getHeight(0);
                if (width <= 0 || height <= 0 || width * height > 16000000L)
                    return JsonVO.create(null, 9999, "头像尺寸过大");
                if (reader.read(0) == null) return JsonVO.create(null, 9999, "图片内容损坏");
                extension = format.equals("png") ? "png" : "jpg";
            } finally { reader.dispose(); }
        } catch (IOException | RuntimeException error) {
            return JsonVO.create(null, 9999, "无法读取图片内容");
        }
        String id = UUID.randomUUID().toString().replace("-", "");
        Path root = Paths.get(localRoot).toAbsolutePath().normalize();
        Files.createDirectories(root.resolve("avatars"));
        root = root.toRealPath();
        Path directory = root.resolve("avatars").toRealPath();
        if (!directory.startsWith(root)) throw new IOException("头像目录不能位于附件目录之外");
        Path destination = directory.resolve(id + "." + extension);
        Annex annex = new Annex();
        annex.setId(id);
        String name = file.getOriginalFilename();
        name = name == null ? "avatar." + extension : name.replace('\\', '/');
        name = name.substring(name.lastIndexOf('/') + 1);
        if (name.length() > 128) name = "avatar." + extension;
        annex.setName(name);
        annex.setFileType(extension);
        annex.setSaveType("Local");
        annex.setSavePath("avatars/" + id + "." + extension);
        annex.setRemark("");
        annex.setStatus(0);
        try {
            Files.write(destination, bytes, StandardOpenOption.CREATE_NEW);
            transactionTemplate.execute(status -> {
                if (!annexService.save(annex)) throw new IllegalStateException("头像记录保存失败");
                return null;
            });
        } catch (IOException | RuntimeException error) {
            Files.deleteIfExists(destination);
            throw error;
        }
        Map<String, String> result = new LinkedHashMap<>();
        result.put("id", id);
        result.put("url", "/j7-sysargs/attachment/avatar/" + id);
        return JsonVO.success(result);
    }

    @GetMapping("/{id}")
    public ResponseEntity<byte[]> content(@PathVariable String id) throws IOException {
        Annex annex = annexService.getById(id);
        if (annex == null || !"Local".equals(annex.getSaveType()) || annex.getSavePath() == null ||
                !annex.getSavePath().matches("avatars/[0-9a-f]{32}\\.(png|jpg)")) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "头像不存在");
        }
        Path root = Paths.get(localRoot).toAbsolutePath().normalize().toRealPath();
        Path path = root.resolve(annex.getSavePath()).normalize();
        if (!Files.isRegularFile(path) || !path.toRealPath().startsWith(root) || Files.size(path) > MAX_BYTES)
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "头像不存在");
        String mime = path.toString().endsWith(".png") ? "image/png" : "image/jpeg";
        return ResponseEntity.ok().contentType(MediaType.parseMediaType(mime))
                .header("X-Content-Type-Options", "nosniff")
                .header(HttpHeaders.CACHE_CONTROL, "private, no-store")
                .body(Files.readAllBytes(path));
    }
}
