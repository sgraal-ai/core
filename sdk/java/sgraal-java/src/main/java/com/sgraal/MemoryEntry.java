package com.sgraal;

public class MemoryEntry {
    public String id;
    public String content;
    public String type;
    public int timestampAgeDays;
    public double sourceTrust;
    public double sourceConflict;
    public int downstreamCount;

    public MemoryEntry(String id, String content, String type, int timestampAgeDays,
                       double sourceTrust, double sourceConflict, int downstreamCount) {
        this.id = id; this.content = content; this.type = type;
        this.timestampAgeDays = timestampAgeDays; this.sourceTrust = sourceTrust;
        this.sourceConflict = sourceConflict; this.downstreamCount = downstreamCount;
    }
}
