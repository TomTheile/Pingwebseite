from app_multi import app  # noqa: F401
from multi_ping_service import MultiPingService

# Initialize the ping service instance (Singleton)
# This ensures that the service is available for the entire application lifecycle
ping_service = MultiPingService()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)