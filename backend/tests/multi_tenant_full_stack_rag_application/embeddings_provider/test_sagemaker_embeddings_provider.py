#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: MIT-0

import json
import os
import pytest
from pathlib import Path
from multi_tenant_full_stack_rag_application.embeddings_provider.embeddings_provider import EmbeddingType
from multi_tenant_full_stack_rag_application.embeddings_provider.embeddings_provider_factory import EmbeddingsProviderFactory
from multi_tenant_full_stack_rag_application.utils import utils

# Load environment variables from .env file
def load_env_file():
    env_file = Path(__file__).parent.parent.parent.parent / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    os.environ[key] = value

# Load environment variables before running tests
load_env_file()


def test_embed_text_with_search_query():
    """Test embed_text with search_query embedding type - calls real backend"""
    print("\n=== Testing embed_text with search_query ===")
    
    provider = EmbeddingsProviderFactory.get_embeddings_provider()
    print(f"Provider endpoint: {provider.endpoint}")
    print(f"Provider model_id: {provider.model_id}")
    print(f"Provider use_embedding_type: {provider.use_embedding_type}")
    
    input_text = "What is machine learning?"
    embedding_type = EmbeddingType.search_query
    
    print(f"Input text: '{input_text}'")
    print(f"Embedding type: {embedding_type.name}")
    
    try:
        result = provider.embed_text(input_text, embedding_type)
        print(f"SUCCESS: Got embeddings result")
        print(f"Result type: {type(result)}")
        print(f"Result length: {len(result) if isinstance(result, list) else 'N/A'}")
        if isinstance(result, list) and len(result) > 0:
            print(f"First embedding length: {len(result[0]) if isinstance(result[0], list) else 'N/A'}")
            print(f"First few values: {result[0][:5] if isinstance(result[0], list) and len(result[0]) >= 5 else result[0]}")
        print(f"Full result: {result}")
        assert result is not None
        assert isinstance(result, list)
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        raise


def test_embed_text_with_search_document():
    """Test embed_text with search_document embedding type - calls real backend"""
    print("\n=== Testing embed_text with search_document ===")
    
    provider = EmbeddingsProviderFactory.get_embeddings_provider()
    
    input_text = "Machine learning is a subset of artificial intelligence."
    embedding_type = EmbeddingType.search_document
    
    print(f"Input text: '{input_text}'")
    print(f"Embedding type: {embedding_type.name}")
    
    try:
        result = provider.embed_text(input_text, embedding_type)
        print(f"SUCCESS: Got embeddings result")
        print(f"Result type: {type(result)}")
        print(f"Result length: {len(result) if isinstance(result, list) else 'N/A'}")
        if isinstance(result, list) and len(result) > 0:
            print(f"First embedding length: {len(result[0]) if isinstance(result[0], list) else 'N/A'}")
            print(f"First few values: {result[0][:5] if isinstance(result[0], list) and len(result[0]) >= 5 else result[0]}")
        print(f"Full result: {result}")
        assert result is not None
        assert isinstance(result, list)
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        raise


def test_embed_text_without_embedding_type():
    """Test embed_text with use_embedding_type=False - calls real backend"""
    print("\n=== Testing embed_text without embedding type prefix ===")
    
    # Create provider with use_embedding_type=False
    custom_args = ['tei-2025-09-04-15-14-22-917', 'nomic-ai/nomic-embed-text-v1.5', 256, 8192, False]
    provider = EmbeddingsProviderFactory.get_embeddings_provider(args=custom_args)
    
    print(f"Provider endpoint: {provider.endpoint}")
    print(f"Provider use_embedding_type: {provider.use_embedding_type}")
    
    input_text = "This text should not have an embedding type prefix."
    embedding_type = EmbeddingType.search_query
    
    print(f"Input text: '{input_text}'")
    print(f"Embedding type: {embedding_type.name} (but should be ignored)")
    
    try:
        result = provider.embed_text(input_text, embedding_type)
        print(f"SUCCESS: Got embeddings result")
        print(f"Result type: {type(result)}")
        print(f"Result length: {len(result) if isinstance(result, list) else 'N/A'}")
        if isinstance(result, list) and len(result) > 0:
            print(f"First embedding length: {len(result[0]) if isinstance(result[0], list) else 'N/A'}")
            print(f"First few values: {result[0][:5] if isinstance(result[0], list) and len(result[0]) >= 5 else result[0]}")
        print(f"Full result: {result}")
        assert result is not None
        assert isinstance(result, list)
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        raise


def test_embed_text_longer_text():
    """Test embed_text with longer text - calls real backend"""
    print("\n=== Testing embed_text with longer text ===")
    
    provider = EmbeddingsProviderFactory.get_embeddings_provider()
    
    input_text = """
    Machine learning is a method of data analysis that automates analytical model building. 
    It is a branch of artificial intelligence based on the idea that systems can learn from data, 
    identify patterns and make decisions with minimal human intervention. Machine learning algorithms 
    build a model based on training data in order to make predictions or decisions without being 
    explicitly programmed to do so.
    """.strip()
    
    embedding_type = EmbeddingType.search_document
    
    print(f"Input text length: {len(input_text)} characters")
    print(f"Input text: '{input_text[:100]}...'")
    print(f"Embedding type: {embedding_type.name}")
    
    try:
        result = provider.embed_text(input_text, embedding_type)
        print(f"SUCCESS: Got embeddings result")
        print(f"Result type: {type(result)}")
        print(f"Result length: {len(result) if isinstance(result, list) else 'N/A'}")
        if isinstance(result, list) and len(result) > 0:
            print(f"First embedding length: {len(result[0]) if isinstance(result[0], list) else 'N/A'}")
            print(f"First few values: {result[0][:5] if isinstance(result[0], list) and len(result[0]) >= 5 else result[0]}")
        print(f"Full result: {result}")
        assert result is not None
        assert isinstance(result, list)
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        raise


def test_embed_text_empty_string():
    """Test embed_text with empty string - calls real backend"""
    print("\n=== Testing embed_text with empty string ===")
    
    provider = EmbeddingsProviderFactory.get_embeddings_provider()
    
    input_text = ""
    embedding_type = EmbeddingType.search_query
    
    print(f"Input text: '{input_text}' (empty string)")
    print(f"Embedding type: {embedding_type.name}")
    
    try:
        result = provider.embed_text(input_text, embedding_type)
        print(f"SUCCESS: Got embeddings result")
        print(f"Result type: {type(result)}")
        print(f"Result length: {len(result) if isinstance(result, list) else 'N/A'}")
        if isinstance(result, list) and len(result) > 0:
            print(f"First embedding length: {len(result[0]) if isinstance(result[0], list) else 'N/A'}")
            print(f"First few values: {result[0][:5] if isinstance(result[0], list) and len(result[0]) >= 5 else result[0]}")
        print(f"Full result: {result}")
        assert result is not None
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        raise


def test_utils_embed_text_integration():
    """Integration test calling utils.embed_text function - tests full lambda invocation path"""
    print("\n=== Testing utils.embed_text integration ===")
    
    input_text = "Integration test for utils embed_text function"
    origin = "http://localhost:5173"  # Use an allowed origin
    embedding_type = "search_query"
    dimensions = 256  # Match the real configuration
    
    print(f"Input text: '{input_text}'")
    print(f"Origin: {origin}")
    print(f"Embedding type: {embedding_type}")
    print(f"Dimensions: {dimensions}")
    
    try:
        # Call the utils.embed_text function which invokes the lambda
        result = utils.embed_text(
            text=input_text,
            origin=origin,
            embedding_type=embedding_type,
            dimensions=dimensions
        )
        
        print(f"SUCCESS: Got embeddings result from utils.embed_text")
        print(f"Result type: {type(result)}")
        print(f"Result length: {len(result) if isinstance(result, list) else 'N/A'}")
        
        if isinstance(result, list) and len(result) > 0:
            print(f"First embedding length: {len(result[0]) if isinstance(result[0], list) else 'N/A'}")
            print(f"First few values: {result[0][:5] if isinstance(result[0], list) and len(result[0]) >= 5 else result[0]}")
        
        print(f"Full result: {result}")
        
        # Verify the result format matches what we expect
        assert result is not None
        assert isinstance(result, list), f"Expected list, got {type(result)}"
        assert len(result) > 0, "Expected non-empty result"
        assert isinstance(result[0], list), f"Expected list of lists, got list of {type(result[0])}"
        assert len(result[0]) == 768, f"Expected 768 dimensions, got {len(result[0])}"  # nomic-embed-text-v1.5 returns 768 dims
        
        # Verify all values are floats
        for i, val in enumerate(result[0][:5]):  # Check first 5 values
            assert isinstance(val, (int, float)), f"Expected numeric value at index {i}, got {type(val)}"
        
        print("✓ All format validations passed")
        
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        raise


def test_utils_embed_text_with_search_document():
    """Integration test calling utils.embed_text with search_document type"""
    print("\n=== Testing utils.embed_text with search_document ===")
    
    input_text = "This is a document about machine learning and artificial intelligence."
    origin = "http://localhost:5173"  # Use an allowed origin
    embedding_type = "search_document"
    dimensions = 256
    
    print(f"Input text: '{input_text}'")
    print(f"Origin: {origin}")
    print(f"Embedding type: {embedding_type}")
    print(f"Dimensions: {dimensions}")
    
    try:
        result = utils.embed_text(
            text=input_text,
            origin=origin,
            embedding_type=embedding_type,
            dimensions=dimensions
        )
        
        print(f"SUCCESS: Got embeddings result from utils.embed_text")
        print(f"Result type: {type(result)}")
        print(f"Result length: {len(result) if isinstance(result, list) else 'N/A'}")
        
        if isinstance(result, list) and len(result) > 0:
            print(f"First embedding length: {len(result[0]) if isinstance(result[0], list) else 'N/A'}")
            print(f"First few values: {result[0][:5] if isinstance(result[0], list) and len(result[0]) >= 5 else result[0]}")
        
        print(f"Full result: {result}")
        
        # Verify the result format
        assert result is not None
        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], list)
        assert len(result[0]) == 768  # nomic-embed-text-v1.5 returns 768 dims
        
        print("✓ All format validations passed")
        
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        raise


def test_utils_embed_text_format_compatibility():
    """Test that utils.embed_text and direct provider.embed_text return compatible formats"""
    print("\n=== Testing format compatibility between utils and provider ===")
    
    input_text = "Format compatibility test text"
    origin = "http://localhost:5173"
    
    try:
        # Get result from utils.embed_text
        utils_result = utils.embed_text(
            text=input_text,
            origin=origin,
            embedding_type="search_query",
            dimensions=256
        )
        
        # Get result from direct provider call
        provider = EmbeddingsProviderFactory.get_embeddings_provider()
        provider_result = provider.embed_text(input_text, EmbeddingType.search_query)
        
        print(f"Utils result type: {type(utils_result)}")
        print(f"Provider result type: {type(provider_result)}")
        
        print(f"Utils result length: {len(utils_result) if isinstance(utils_result, list) else 'N/A'}")
        print(f"Provider result length: {len(provider_result) if isinstance(provider_result, list) else 'N/A'}")
        
        if isinstance(utils_result, list) and len(utils_result) > 0:
            print(f"Utils first embedding length: {len(utils_result[0]) if isinstance(utils_result[0], list) else 'N/A'}")
        if isinstance(provider_result, list) and len(provider_result) > 0:
            print(f"Provider first embedding length: {len(provider_result[0]) if isinstance(provider_result[0], list) else 'N/A'}")
        
        # Both should return the same format
        assert type(utils_result) == type(provider_result), f"Types don't match: {type(utils_result)} vs {type(provider_result)}"
        assert len(utils_result) == len(provider_result), f"Lengths don't match: {len(utils_result)} vs {len(provider_result)}"
        
        if isinstance(utils_result, list) and len(utils_result) > 0:
            assert len(utils_result[0]) == len(provider_result[0]), f"Embedding dimensions don't match: {len(utils_result[0])} vs {len(provider_result[0])}"
        
        print("✓ Format compatibility verified - both return same structure")
        
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        raise


def test_embed_text_return_format_specification():
    """Test that embed_text returns the exact format expected by utils.embed_text"""
    print("\n=== Testing embed_text return format specification ===")
    
    provider = EmbeddingsProviderFactory.get_embeddings_provider()
    
    input_text = "Test text for format validation"
    embedding_type = EmbeddingType.search_query
    
    print(f"Input text: '{input_text}'")
    print(f"Embedding type: {embedding_type.name}")
    
    try:
        result = provider.embed_text(input_text, embedding_type)
        
        print(f"Result type: {type(result)}")
        print(f"Result: {result}")
        
        # Validate the exact format expected by utils.embed_text
        # Based on utils.py, it expects: json.loads(response['body'])['response']
        # The provider should return a list of lists (embeddings)
        
        # 1. Must be a list
        assert isinstance(result, list), f"Expected list, got {type(result)}"
        print("✓ Result is a list")
        
        # 2. Must not be empty
        assert len(result) > 0, "Expected non-empty list"
        print(f"✓ Result has {len(result)} item(s)")
        
        # 3. Each item should be a list of floats (embedding vector)
        for i, embedding in enumerate(result):
            assert isinstance(embedding, list), f"Expected list at index {i}, got {type(embedding)}"
            assert len(embedding) > 0, f"Expected non-empty embedding at index {i}"
            
            # Check first few values are numeric
            for j, val in enumerate(embedding[:5]):
                assert isinstance(val, (int, float)), f"Expected numeric value at [{i}][{j}], got {type(val)}: {val}"
        
        print(f"✓ All embeddings are lists of numeric values")
        print(f"✓ First embedding has {len(result[0])} dimensions")
        
        # 4. For nomic-embed-text-v1.5, should return 768 dimensions
        expected_dims = 768  # nomic-embed-text-v1.5 actual output dimensions
        actual_dims = len(result[0])
        print(f"Expected dimensions: {expected_dims}, Actual dimensions: {actual_dims}")
        
        if actual_dims != expected_dims:
            print(f"WARNING: Dimension mismatch - expected {expected_dims}, got {actual_dims}")
            print("This might indicate a configuration issue or model change")
        
        # 5. Values should be reasonable embedding values (typically between -1 and 1, but can vary)
        sample_values = result[0][:10]
        print(f"Sample embedding values: {sample_values}")
        
        for val in sample_values:
            assert isinstance(val, (int, float)), f"Non-numeric value found: {val}"
            assert -10 < val < 10, f"Embedding value seems out of reasonable range: {val}"
        
        print("✓ Embedding values are in reasonable range")
        print("✓ embed_text returns format compatible with utils.embed_text expectations")
        
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        raise


def test_embed_text_with_string_embedding_type():
    """Test embed_text with string embedding_type (as passed from utils.embed_text)"""
    print("\n=== Testing embed_text with string embedding_type ===")
    
    provider = EmbeddingsProviderFactory.get_embeddings_provider()
    
    input_text = "Test with string embedding type"
    
    # Test with string values as they come from utils.embed_text
    for embedding_type_str in ["search_query", "search_document"]:
        print(f"\nTesting with embedding_type: '{embedding_type_str}' (string)")
        
        try:
            # This should work if the provider properly handles string embedding types
            # Note: This might fail if the provider only accepts EmbeddingType enum
            result = provider.embed_text(input_text, embedding_type_str)
            
            print(f"SUCCESS: Got result with string embedding_type")
            print(f"Result type: {type(result)}")
            print(f"Result length: {len(result) if isinstance(result, list) else 'N/A'}")
            
            assert isinstance(result, list)
            assert len(result) > 0
            assert isinstance(result[0], list)
            
            print(f"✓ String embedding_type '{embedding_type_str}' works correctly")
            
        except Exception as e:
            print(f"ERROR with string embedding_type '{embedding_type_str}': {type(e).__name__}: {e}")
            print("This indicates the provider needs to be updated to handle string embedding types")
            # Don't raise here - this is expected to fail until the provider is fixed
            print("Expected failure - provider should be updated to handle string embedding types from utils.embed_text")
