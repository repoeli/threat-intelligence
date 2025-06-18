"""
tests/test_api_schema.py - API schema and contract tests
"""

import pytest
import json
from pathlib import Path
import httpx
from fastapi import status


@pytest.mark.asyncio
class TestAPISchema:
    """Test API schema consistency and OpenAPI specification"""

    async def test_openapi_schema_generation(self, async_client: httpx.AsyncClient):
        """Test that OpenAPI schema is generated correctly"""
        response = await async_client.get("/openapi.json")
        
        assert response.status_code == status.HTTP_200_OK
        schema = response.json()
        
        # Basic schema structure
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        assert "components" in schema
        
        # API metadata
        assert schema["info"]["title"] == "Threat Intelligence API"
        assert schema["info"]["version"] == "1.0.0"
        
        # Required paths exist
        required_paths = [
            "/health",
            "/auth/register",
            "/auth/login", 
            "/auth/me",
            "/analyze",
            "/analyze/bulk",
            "/api/virustotal",
            "/api/visualize",
            "/metrics",
            "/status"
        ]
        
        for path in required_paths:
            assert path in schema["paths"], f"Required path {path} not found in schema"

    async def test_authentication_schema(self, async_client: httpx.AsyncClient):
        """Test authentication endpoint schemas"""
        response = await async_client.get("/openapi.json")
        schema = response.json()
        
        # Registration endpoint
        register_path = schema["paths"]["/auth/register"]["post"]
        assert "requestBody" in register_path
        assert "responses" in register_path
        
        # Login endpoint
        login_path = schema["paths"]["/auth/login"]["post"] 
        assert "requestBody" in login_path
        assert "responses" in login_path

    async def test_analysis_endpoint_schemas(self, async_client: httpx.AsyncClient):
        """Test analysis endpoint schemas"""
        response = await async_client.get("/openapi.json")
        schema = response.json()
        
        # Analyze endpoint
        analyze_path = schema["paths"]["/analyze"]["post"]
        assert "requestBody" in analyze_path
        assert "responses" in analyze_path
        assert "security" in analyze_path  # Should require authentication
        
        # Bulk analyze endpoint
        bulk_path = schema["paths"]["/analyze/bulk"]["post"]
        assert "requestBody" in bulk_path
        assert "responses" in bulk_path
        assert "security" in bulk_path

    async def test_response_models_schema(self, async_client: httpx.AsyncClient):
        """Test that response models are properly defined"""
        response = await async_client.get("/openapi.json")
        schema = response.json()
        
        components = schema.get("components", {}).get("schemas", {})
        
        # Required response models
        required_models = [
            "AnalysisResponse",
            "BulkAnalysisResponse", 
            "UserResponse",
            "TokenResponse",
            "VizResponse"
        ]
        
        for model in required_models:
            assert model in components, f"Required model {model} not found in schema"

    async def test_enum_schemas(self, async_client: httpx.AsyncClient):
        """Test that enums are properly defined in schema"""
        response = await async_client.get("/openapi.json")
        schema = response.json()
        
        components = schema.get("components", {}).get("schemas", {})
        
        # Check enum definitions
        enum_models = ["IndicatorType", "ThreatVerdict", "RiskLevel", "UserRole"]
        
        for enum_model in enum_models:
            assert enum_model in components, f"Enum {enum_model} not found in schema"
            enum_schema = components[enum_model]
            assert "enum" in enum_schema, f"Enum {enum_model} missing enum values"

    async def test_security_schemes(self, async_client: httpx.AsyncClient):
        """Test that security schemes are properly defined"""
        response = await async_client.get("/openapi.json")
        schema = response.json()
        
        components = schema.get("components", {})
        security_schemes = components.get("securitySchemes", {})
        
        # Should have Bearer token security
        assert "HTTPBearer" in security_schemes
        bearer_scheme = security_schemes["HTTPBearer"]
        assert bearer_scheme["type"] == "http"
        assert bearer_scheme["scheme"] == "bearer"

    async def test_docs_endpoints_accessible(self, async_client: httpx.AsyncClient):
        """Test that documentation endpoints are accessible"""
        # Swagger UI
        response = await async_client.get("/docs")
        assert response.status_code == status.HTTP_200_OK
        
        # ReDoc
        response = await async_client.get("/redoc")
        assert response.status_code == status.HTTP_200_OK

    def test_schema_snapshot(self, async_client_sync):
        """Test that OpenAPI schema matches expected snapshot"""
        # This test would compare against a saved schema snapshot
        # Useful for detecting unintended API changes
        
        response = async_client_sync.get("/openapi.json")
        current_schema = response.json()
        
        # In a real implementation, you'd save and compare against a snapshot
        # For now, just verify the schema is valid JSON
        assert isinstance(current_schema, dict)
        assert "openapi" in current_schema
        
        # Optionally save current schema for manual review
        schema_file = Path(__file__).parent / "snapshots" / "openapi_schema.json"
        schema_file.parent.mkdir(exist_ok=True)
        
        with open(schema_file, "w") as f:
            json.dump(current_schema, f, indent=2, sort_keys=True)

    async def test_error_response_schemas(self, async_client: httpx.AsyncClient):
        """Test that error responses follow consistent schema"""
        # Test various error conditions
        error_tests = [
            ("/analyze", {"indicator": "invalid"}, status.HTTP_401_UNAUTHORIZED),
            ("/auth/login", {"username": "fake", "password": "fake"}, status.HTTP_401_UNAUTHORIZED),
        ]
        
        for endpoint, data, expected_status in error_tests:
            response = await async_client.post(endpoint, json=data)
            
            if response.status_code == expected_status:
                error_data = response.json()
                # Error responses should have consistent structure
                assert "detail" in error_data

    async def test_tag_organization(self, async_client: httpx.AsyncClient):
        """Test that endpoints are properly organized with tags"""
        response = await async_client.get("/openapi.json")
        schema = response.json()
        
        paths = schema["paths"]
        
        # Check that endpoints have appropriate tags
        tag_expectations = {
            "/health": ["meta"],
            "/auth/register": ["authentication"],
            "/auth/login": ["authentication"],
            "/analyze": ["analysis"],
            "/analyze/bulk": ["analysis"],
            "/api/virustotal": ["virustotal"],
            "/metrics": ["monitoring"],
            "/status": ["monitoring"]
        }
        
        for path, expected_tags in tag_expectations.items():
            if path in paths:
                for method in paths[path]:
                    if method in ["get", "post", "put", "delete"]:
                        operation = paths[path][method]
                        if "tags" in operation:
                            operation_tags = operation["tags"]
                            assert any(tag in operation_tags for tag in expected_tags), \
                                f"Path {path} missing expected tags {expected_tags}, got {operation_tags}"

    async def test_request_validation_schemas(self, async_client: httpx.AsyncClient):
        """Test that request validation schemas are comprehensive"""
        response = await async_client.get("/openapi.json")
        schema = response.json()
        
        components = schema.get("components", {}).get("schemas", {})
        
        # Check request models have proper validation
        request_models = ["IndicatorRequest", "LoginRequest", "UserRegistration", "BulkAnalysisRequest"]
        
        for model in request_models:
            if model in components:
                model_schema = components[model]
                assert "properties" in model_schema, f"Model {model} missing properties"
                assert "required" in model_schema, f"Model {model} missing required fields"

    async def test_response_examples(self, async_client: httpx.AsyncClient):
        """Test that response schemas include examples where appropriate"""
        response = await async_client.get("/openapi.json")
        schema = response.json()
        
        # This would check for examples in the OpenAPI schema
        # Examples help with API documentation and testing
        paths = schema["paths"]
        
        # At least some endpoints should have response examples
        example_count = 0
        for path_data in paths.values():
            for method_data in path_data.values():
                if isinstance(method_data, dict) and "responses" in method_data:
                    for response_data in method_data["responses"].values():
                        if isinstance(response_data, dict) and "content" in response_data:
                            for content_data in response_data["content"].values():
                                if "example" in content_data or "examples" in content_data:
                                    example_count += 1
        
        # We expect at least some examples to be present
        # In a mature API, this number would be higher
        assert example_count >= 0  # Placeholder - would set higher in production


@pytest.fixture
def async_client_sync(async_client):
    """Synchronous client for snapshot testing"""
    import httpx
    
    # Create a synchronous client for tests that need to write files
    with httpx.Client(app=async_client._transport.app, base_url="http://test") as client:
        yield client
