import time
import requests
import json
import argparse
import concurrent.futures
from typing import List, Dict, Any

def measure_tokens_per_second(api_url: str, model_name: str, prompt: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
    """
    Measure tokens per second from the OpenAI-compatible API.
    
    Args:
        api_url: Base URL of the API
        model_name: Name of the model to use
        prompt: Input prompt for generation
        max_tokens: Maximum number of tokens to generate
        temperature: Sampling temperature
    
    Returns:
        Dictionary containing timing, token, and performance metrics
    """
    # API configuration
    endpoint = f"{api_url}/completions"
    
    # Request payload
    payload = {
        "model": model_name,
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False
    }
    
    # Headers
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        # Record start time
        start_time = time.time()
        
        # Make the API request
        response = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Record end time
        end_time = time.time()
        
        # Parse response
        result = response.json()
        
        # Extract token information
        # For token count, we'll estimate based on response length if not provided
        # Some APIs don't return exact token counts
        response_text = result.get('choices', [{}])[0].get('text', '')
        # Rough estimation: 4 characters per token (English text)
        output_tokens = max(1, len(response_text) // 4)
        
        # Calculate tokens per second
        elapsed_time = end_time - start_time
        
        # Return detailed metrics
        return {
            "success": True,
            "response_time": elapsed_time,
            "output_tokens": output_tokens,
            "tokens_per_second": output_tokens / elapsed_time if elapsed_time > 0 else 0,
            "status_code": response.status_code,
            "error": None
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "response_time": 0,
            "output_tokens": 0,
            "tokens_per_second": 0,
            "status_code": e.response.status_code if hasattr(e, 'response') and e.response is not None else 0,
            "error": str(e)
        }
    except Exception as e:
        return {
            "success": False,
            "response_time": 0,
            "output_tokens": 0,
            "tokens_per_second": 0,
            "status_code": 0,
            "error": str(e)
        }

def run_single_test(api_url: str, model_name: str, prompt: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
    """Run a single token rate measurement test."""
    return measure_tokens_per_second(api_url, model_name, prompt, max_tokens, temperature)

def run_concurrent_tests(api_url: str, model_name: str, prompt: str, max_tokens: int,
                        temperature: float, num_connections: int) -> List[Dict[str, Any]]:
    """
    Run multiple token rate measurements concurrently.
    
    Args:
        api_url: Base URL of the API
        model_name: Name of the model to use
        prompt: Input prompt for generation
        max_tokens: Maximum number of tokens to generate
        temperature: Sampling temperature
        num_connections: Number of simultaneous connections
    
    Returns:
        List of results from all concurrent tests
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_connections) as executor:
        # Submit all requests
        future_to_index = {
            executor.submit(
                measure_tokens_per_second,
                api_url, model_name, prompt, max_tokens, temperature
            ): i for i in range(num_connections)
        }
        
        # Collect results
        results = []
        for future in concurrent.futures.as_completed(future_to_index):
            result = future.result()
            results.append(result)
            
    return results

def calculate_statistics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate statistical metrics from test results.
    
    Args:
        results: List of test results
        
    Returns:
        Dictionary containing statistical analysis
    """
    successful_results = [r for r in results if r["success"]]
    
    if not successful_results:
        return {
            "total_requests": len(results),
            "successful_requests": 0,
            "failure_rate": 1.0,
            "avg_response_time": 0,
            "median_response_time": 0,
            "min_response_time": 0,
            "max_response_time": 0,
            "avg_tokens_per_second": 0,
            "median_tokens_per_second": 0,
            "min_tokens_per_second": 0,
            "max_tokens_per_second": 0,
            "total_tokens_generated": 0
        }
    
    response_times = sorted([r["response_time"] for r in successful_results])
    tokens_per_second = sorted([r["tokens_per_second"] for r in successful_results])
    total_tokens = sum([r["output_tokens"] for r in successful_results])
    
    def median(values):
        n = len(values)
        if n % 2 == 1:
            return values[n // 2]
        else:
            return (values[n // 2 - 1] + values[n // 2]) / 2
    
    return {
        "total_requests": len(results),
        "successful_requests": len(successful_results),
        "failure_rate": 1 - (len(successful_results) / len(results)),
        "avg_response_time": sum(response_times) / len(response_times),
        "median_response_time": median(response_times),
        "min_response_time": min(response_times),
        "max_response_time": max(response_times),
        "avg_tokens_per_second": sum(tokens_per_second) / len(tokens_per_second),
        "median_tokens_per_second": median(tokens_per_second),
        "min_tokens_per_second": min(tokens_per_second),
        "max_tokens_per_second": max(tokens_per_second),
        "total_tokens_generated": total_tokens
    }

def print_statistics(stats: Dict[str, Any], num_connections: int):
    """Print statistical results in a formatted way."""
    print(f"\n{'='*50}")
    print(f"CONCURRENT TEST RESULTS ({num_connections} simultaneous connections)")
    print(f"{'='*50}")
    print(f"Total Requests: {stats['total_requests']}")
    print(f"Successful Requests: {stats['successful_requests']}")
    print(f"Failure Rate: {stats['failure_rate']:.2%}")
    print(f"Total Tokens Generated: {stats['total_tokens_generated']:,}")
    print(f"\nRESPONSE TIME (seconds):")
    print(f"  Average: {stats['avg_response_time']:.3f}")
    print(f"  Median:  {stats['median_response_time']:.3f}")
    print(f"  Min:     {stats['min_response_time']:.3f}")
    print(f"  Max:     {stats['max_response_time']:.3f}")
    print(f"\nTOKENS PER SECOND:")
    print(f"  Average: {stats['avg_tokens_per_second']:.2f}")
    print(f"  Median:  {stats['median_tokens_per_second']:.2f}")
    print(f"  Min:     {stats['min_tokens_per_second']:.2f}")
    print(f"  Max:     {stats['max_tokens_per_second']:.2f}")

def main():
    """Main function to execute the token rate measurement with command line arguments."""
    parser = argparse.ArgumentParser(description='Measure tokens per second from an API with concurrent connections.')
    parser.add_argument('--api-url', type=str, default="http://localhost:9991/v1",
                       help='Base URL of the API (default: http://localhost:9991/v1)')
    parser.add_argument('--model', type=str, default="llm_model",
                       help='Name of the model to use (default: llm_model)')
    parser.add_argument('--prompt', type=str,
                       default="The quick brown fox jumps over the lazy dog. " * 10,
                       help='Input prompt for generation')
    parser.add_argument('--max-tokens', type=int, default=1000,
                       help='Maximum number of tokens to generate (default: 1000)')
    parser.add_argument('--temperature', type=float, default=0.7,
                       help='Sampling temperature (default: 0.7)')
    parser.add_argument('--connections', type=int, default=1,
                       help='Number of simultaneous connections (default: 1)')
    
    args = parser.parse_args()
    
    print("Measuring tokens per second from API...")
    print(f"Endpoint: {args.api_url}")
    print(f"Model: {args.model}")
    print(f"Simultaneous Connections: {args.connections}")
    print(f"Max Tokens: {args.max_tokens}")
    print("-" * 50)
    
    # Run concurrent tests
    results = run_concurrent_tests(
        args.api_url, args.model, args.prompt,
        args.max_tokens, args.temperature, args.connections
    )
    
    # Calculate and print statistics
    stats = calculate_statistics(results)
    print_statistics(stats, args.connections)
    
    # Return average tokens per second for backward compatibility
    if stats["successful_requests"] > 0:
        print(f"\nRESULT: {stats['avg_tokens_per_second']:.2f} tokens/second")
        return stats['avg_tokens_per_second']
    else:
        print("Failed to measure tokens per second.")
        return None

if __name__ == "__main__":
    main()