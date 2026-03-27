package sgraal
import ("encoding/json";"fmt";"net/http";"bytes")
type Client struct { APIKey, BaseURL string }
type PreflightResult struct { OmegaMemFinal float64 `json:"omega_mem_final"`; RecommendedAction string `json:"recommended_action"` }
func NewClient(apiKey string) *Client { return &Client{APIKey: apiKey, BaseURL: "https://api.sgraal.com"} }
func (c *Client) Preflight(memoryState []map[string]interface{}) (*PreflightResult, error) {
	body, _ := json.Marshal(map[string]interface{}{"memory_state": memoryState})
	req, _ := http.NewRequest("POST", c.BaseURL+"/v1/preflight", bytes.NewReader(body))
	req.Header.Set("Authorization", "Bearer "+c.APIKey)
	req.Header.Set("Content-Type", "application/json")
	resp, err := http.DefaultClient.Do(req)
	if err != nil { return nil, err }
	defer resp.Body.Close()
	var result PreflightResult
	json.NewDecoder(resp.Body).Decode(&result)
	return &result, nil
}
func (c *Client) Heal() error { return fmt.Errorf("Coming in next release") }
func (c *Client) Batch() error { return fmt.Errorf("Coming in next release") }
