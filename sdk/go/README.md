# Sgraal Go SDK

Go client for the Sgraal Memory Governance API.

## Install
```bash
go get github.com/sgraal-ai/sgraal-go
```

## Usage
```go
package main

import (
    "context"
    "fmt"
    sgraal "github.com/sgraal-ai/sgraal-go"
)

func main() {
    client := sgraal.NewClient("sg_demo_playground")
    result, err := client.Preflight(context.Background(), sgraal.PreflightRequest{
        MemoryState: []sgraal.MemoryEntry{{
            ID: "mem_001", Content: "Customer prefers email",
            Type: "preference", TimestampAgeDays: 5,
            SourceTrust: 0.9, SourceConflict: 0.05, DownstreamCount: 1,
        }},
        Domain:     "general",
        ActionType: "reversible",
    })
    if err != nil {
        panic(err)
    }
    fmt.Println("Decision:", result.RecommendedAction)
}
```
