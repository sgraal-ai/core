namespace Sgraal.Models;
public class MemoryEntry
{
    public string Id { get; set; } = "";
    public string Content { get; set; } = "";
    public string Type { get; set; } = "semantic";
    public double TimestampAgeDays { get; set; }
    public double SourceTrust { get; set; } = 0.9;
    public double SourceConflict { get; set; } = 0.05;
    public int DownstreamCount { get; set; } = 1;
}
