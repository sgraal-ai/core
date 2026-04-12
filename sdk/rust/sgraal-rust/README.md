# Sgraal Rust SDK
Rust client for the [Sgraal](https://sgraal.com) Memory Governance API.
## Install
```toml
[dependencies]
sgraal = "0.1.0"
```
## Usage
```rust
let client = sgraal::SgraalClient::new("sg_demo_playground");
let result = client.preflight(req).await?;
println!("Decision: {}", result.recommended_action);
```
