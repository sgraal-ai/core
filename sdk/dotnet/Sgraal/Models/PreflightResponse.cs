namespace Sgraal.Models;
public class PreflightResponse
{
    public string RecommendedAction { get; set; } = "";
    public double OmegaMemFinal { get; set; }
    public string AttackSurfaceLevel { get; set; } = "NONE";
    public string RequestId { get; set; } = "";
}
