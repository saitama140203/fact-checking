import pymongo, certifi
import socket
import ssl

# Test 1: DNS Resolution cho tất cả các node
print("=== TEST 1: DNS RESOLUTION ===")
hosts = [
    "detect-fake-news.adxo4na.mongodb.net",
    "ac-n7ikbz2-shard-00-00.adxo4na.mongodb.net",
    "ac-n7ikbz2-shard-00-01.adxo4na.mongodb.net",
    "ac-n7ikbz2-shard-00-02.adxo4na.mongodb.net"
]

for host in hosts:
    try:
        ip = socket.gethostbyname(host)
        print(f"✅ {host} -> {ip}")
    except Exception as e:
        print(f"❌ {host}: {e}")

# Test 2: Port connectivity
print("\n=== TEST 2: PORT 27017 CONNECTIVITY ===")
for host in hosts[1:]:  # Skip SRV, test actual nodes
    try:
        sock = socket.create_connection((host, 27017), timeout=5)
        print(f"✅ {host}:27017 - Port mở")
        sock.close()
    except Exception as e:
        print(f"❌ {host}:27017 - {e}")

# Test 3: SSL/TLS
print("\n=== TEST 3: SSL/TLS HANDSHAKE ===")
context = ssl.create_default_context(cafile=certifi.where())
for host in hosts[1:]:
    try:
        with socket.create_connection((host, 27017), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                print(f"✅ {host} - SSL OK (Protocol: {ssock.version()})")
    except Exception as e:
        print(f"❌ {host} - SSL Error: {e}")

# Test 4: MongoDB Connection
print("\n=== TEST 4: MONGODB CONNECTION ===")
uri = "mongodb+srv://fact-checking:ElSlpvgYUN9Wdabq@detect-fake-news.adxo4na.mongodb.net/?appName=Detect-fake-news"

try:
    client = pymongo.MongoClient(
        uri, 
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=5000
    )
    client.admin.command("ping")
    print("✅ Kết nối MongoDB OK")
except Exception as e:
    print(f"❌ MongoDB Error: {e}")

# Test 4a: MongoDB WITHOUT SSL verification (TESTING ONLY)
print("\n=== TEST 4a: MONGODB (NO SSL VERIFY) ===")
try:
    client = pymongo.MongoClient(
        uri,
        tlsAllowInvalidCertificates=True,
        tlsAllowInvalidHostnames=True,
        serverSelectionTimeoutMS=5000
    )
    client.admin.command("ping")
    print("✅ Kết nối OK khi bỏ SSL verification")
    print("-> Network đang can thiệp vào SSL certificates")
except Exception as e:
    print(f"❌ Vẫn lỗi: {e}")