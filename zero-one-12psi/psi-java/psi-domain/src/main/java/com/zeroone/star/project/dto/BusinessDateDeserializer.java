package com.zeroone.star.project.dto;

import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.core.JsonToken;
import com.fasterxml.jackson.databind.DeserializationContext;
import com.fasterxml.jackson.databind.JsonDeserializer;
import java.io.IOException;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.time.format.ResolverStyle;
import java.util.Date;

/** Business timestamps accept a whole date, a local timestamp, ISO offset time or epoch milliseconds. */
public class BusinessDateDeserializer extends JsonDeserializer<Date> {
    private static final ZoneId ZONE=ZoneId.of("Asia/Shanghai");
    private static final DateTimeFormatter LOCAL=DateTimeFormatter.ofPattern("uuuu-MM-dd HH:mm:ss").withResolverStyle(ResolverStyle.STRICT);
    @Override public Date deserialize(JsonParser parser,DeserializationContext context) throws IOException {
        if(parser.hasToken(JsonToken.VALUE_NUMBER_INT)) return new Date(parser.getLongValue());
        if(!parser.hasToken(JsonToken.VALUE_STRING)) throw context.weirdStringException(parser.getText(),Date.class,"单据日期必须是日期、日期时间或毫秒时间戳");
        String text=parser.getText().trim();
        try {
            if(text.matches("\\d{4}-\\d{2}-\\d{2}")) return Date.from(LocalDate.parse(text).atStartOfDay(ZONE).toInstant());
            if(text.matches("\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}")) return Date.from(LocalDateTime.parse(text,LOCAL).atZone(ZONE).toInstant());
            try { return Date.from(OffsetDateTime.parse(text).toInstant()); }
            catch(java.time.format.DateTimeParseException ignored) { return Date.from(LocalDateTime.parse(text).atZone(ZONE).toInstant()); }
        } catch(DateTimeException error) {
            throw context.weirdStringException(text,Date.class,"单据日期无效，请使用真实日期或完整日期时间");
        }
    }
}
