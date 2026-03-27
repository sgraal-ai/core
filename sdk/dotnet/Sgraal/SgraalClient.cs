using System.Net.Http;
using System.Text;
namespace Sgraal {
    public class SgraalClient {
        private readonly string _apiKey;
        private readonly string _baseUrl;
        private readonly HttpClient _http = new();
        public SgraalClient(string apiKey, string baseUrl = "https://api.sgraal.com") { _apiKey = apiKey; _baseUrl = baseUrl; }
        public async Task<string> PreflightAsync(string jsonBody) {
            var req = new HttpRequestMessage(HttpMethod.Post, $"{_baseUrl}/v1/preflight");
            req.Headers.Add("Authorization", $"Bearer {_apiKey}");
            req.Content = new StringContent(jsonBody, Encoding.UTF8, "application/json");
            var resp = await _http.SendAsync(req);
            return await resp.Content.ReadAsStringAsync();
        }
        public Task<string> HealAsync() => throw new NotImplementedException("Coming in next release");
        public Task<string> BatchAsync() => throw new NotImplementedException("Coming in next release");
    }
}
