# Sgraal Java SDK
Java client for the [Sgraal](https://sgraal.com) Memory Governance API.
## Install
Add to pom.xml: `com.sgraal:sgraal-java:0.1.0`
## Usage
```java
SgraalClient client = new SgraalClient("sg_demo_playground");
String result = client.preflight("{\"memory_state\":[...],\"domain\":\"general\"}");
```
