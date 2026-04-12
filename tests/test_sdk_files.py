"""Tests verifying SDK files exist for Java, Rust, C#, gRPC."""
import pytest
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestSDKFiles:
    def test_java_sdk_files_exist(self):
        assert os.path.exists(os.path.join(_ROOT, "sdk/java/sgraal-java/pom.xml"))
        assert os.path.exists(os.path.join(_ROOT, "sdk/java/sgraal-java/src/main/java/com/sgraal/SgraalClient.java"))

    def test_rust_sdk_files_exist(self):
        assert os.path.exists(os.path.join(_ROOT, "sdk/rust/sgraal-rust/Cargo.toml"))
        assert os.path.exists(os.path.join(_ROOT, "sdk/rust/sgraal-rust/src/lib.rs"))

    def test_dotnet_sdk_files_exist(self):
        assert os.path.exists(os.path.join(_ROOT, "sdk/dotnet/Sgraal/Sgraal.csproj"))

    def test_grpc_proto_exists(self):
        proto_path = os.path.join(_ROOT, "api/proto/sgraal.proto")
        assert os.path.exists(proto_path)
        with open(proto_path) as f:
            content = f.read()
        assert "service MemoryGovernance" in content
        assert "rpc Preflight" in content
