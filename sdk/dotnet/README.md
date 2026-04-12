# Sgraal .NET SDK
C# client for the [Sgraal](https://sgraal.com) Memory Governance API.
## Install
`dotnet add package Sgraal`
## Usage
```csharp
var client = new SgraalClient("sg_demo_playground");
var result = await client.PreflightAsync(new PreflightRequest { ... });
Console.WriteLine(result.RecommendedAction);
```
