namespace Sgraal;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using Sgraal.Models;

public class SgraalClient
{
    private readonly HttpClient _http;
    private readonly string _baseUrl;

    public SgraalClient(string apiKey, string baseUrl = "https://api.sgraal.com")
    {
        _baseUrl = baseUrl;
        _http = new HttpClient();
        _http.DefaultRequestHeaders.Add("Authorization", $"Bearer {apiKey}");
    }

    public async Task<PreflightResponse?> PreflightAsync(PreflightRequest request)
    {
        var resp = await _http.PostAsJsonAsync($"{_baseUrl}/v1/preflight", request);
        resp.EnsureSuccessStatusCode();
        return await resp.Content.ReadFromJsonAsync<PreflightResponse>();
    }
}
