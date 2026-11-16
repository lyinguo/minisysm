package com.zeroone.star.project.dto.j2.store;

import lombok.Data;
import java.util.List;
import java.util.Map;
import java.io.IOException;
import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.core.JsonToken;
import com.fasterxml.jackson.databind.DeserializationContext;
import com.fasterxml.jackson.databind.JsonMappingException;
import com.fasterxml.jackson.databind.annotation.JsonDeserialize;
import com.fasterxml.jackson.databind.deser.std.StdDeserializer;

/** Exact document IDs and versions reviewed by the operator; target is never inferred. */
@Data
public class StockDocumentCommand {
    @JsonDeserialize(contentUsing=StringId.class)
    private List<String> ids;
    private Map<String,String> versions;
    @JsonDeserialize(using=StateTarget.class)
    private Integer target;
    public static class StringId extends StdDeserializer<String> {
        public StringId(){super(String.class);}
        @Override public String deserialize(JsonParser parser,DeserializationContext context) throws IOException {
            if(parser.currentToken()!=JsonToken.VALUE_STRING)throw JsonMappingException.from(parser,"单据ID必须使用字符串，不能转换为数字");
            return parser.getText();
        }
    }
    public static class StateTarget extends StdDeserializer<Integer> {
        public StateTarget(){super(Integer.class);}
        @Override public Integer deserialize(JsonParser parser,DeserializationContext context) throws IOException {
            if(parser.currentToken()!=JsonToken.VALUE_NUMBER_INT)throw JsonMappingException.from(parser,"目标状态必须是整数0或1");
            return parser.getIntValue();
        }
    }
}
