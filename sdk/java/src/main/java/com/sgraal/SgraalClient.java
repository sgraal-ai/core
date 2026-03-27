package com.sgraal;
import java.net.http.*;
import java.net.URI;
public class SgraalClient {
    private final String apiKey;
    private final String baseUrl;
    public SgraalClient(String apiKey) { this(apiKey, "https://api.sgraal.com"); }
    public SgraalClient(String apiKey, String baseUrl) { this.apiKey = apiKey; this.baseUrl = baseUrl; }
    public String preflight(String jsonBody) throws Exception {
        var client = HttpClient.newHttpClient();
        var request = HttpRequest.newBuilder().uri(URI.create(baseUrl + "/v1/preflight"))
            .header("Authorization", "Bearer " + apiKey).header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(jsonBody)).build();
        return client.send(request, HttpResponse.BodyHandlers.ofString()).body();
    }
    public String heal() { throw new UnsupportedOperationException("Coming in next release"); }
    public String batch() { throw new UnsupportedOperationException("Coming in next release"); }
}
