package com.sgraal;
import java.util.List;

public class PreflightRequest {
    public List<MemoryEntry> memoryState;
    public String domain;
    public String actionType;

    public PreflightRequest(List<MemoryEntry> memoryState, String domain, String actionType) {
        this.memoryState = memoryState; this.domain = domain; this.actionType = actionType;
    }
}
