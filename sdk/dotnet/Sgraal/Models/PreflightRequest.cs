namespace Sgraal.Models;
using System.Collections.Generic;
public class PreflightRequest
{
    public List<MemoryEntry> MemoryState { get; set; } = new();
    public string Domain { get; set; } = "general";
    public string ActionType { get; set; } = "reversible";
}
