"""
Tests for the network_stats module
"""
import pytest
from unittest.mock import patch, MagicMock
from netdash.network_stats import NetworkStats

class TestNetworkStats:
    """Test suite for NetworkStats class"""
    
    @patch('psutil.net_io_counters')
    def test_get_counters(self, mock_net_io_counters):
        """Test that counters are retrieved correctly"""
        # Create a mock return value for net_io_counters
        mock_counter = MagicMock()
        mock_counter.bytes_sent = 1000
        mock_counter.bytes_recv = 2000
        mock_counter.packets_sent = 10
        mock_counter.packets_recv = 20
        
        mock_net_io_counters.return_value = {'eth0': mock_counter}
        
        # Initialize network stats
        net_stats = NetworkStats()
        
        # Verify counters were retrieved
        assert net_stats.current_counters is not None
        assert 'eth0' in net_stats.current_counters
    
    def test_format_bytes(self):
        """Test byte formatting function"""
        net_stats = NetworkStats()
        
        # Test different byte sizes
        assert net_stats._format_bytes(500) == "500.00 B"
        assert net_stats._format_bytes(1500) == "1.46 KB"
        assert net_stats._format_bytes(1500000) == "1.43 MB"
        assert net_stats._format_bytes(1500000000) == "1.40 GB"
    
    @patch('psutil.net_io_counters')
    def test_calculate_speed(self, mock_net_io_counters):
        """Test speed calculation between updates"""
        # Create mock counters for two points in time
        mock_counter1 = MagicMock()
        mock_counter1.bytes_sent = 1000
        mock_counter1.bytes_recv = 2000
        
        mock_counter2 = MagicMock()
        mock_counter2.bytes_sent = 2500  # 1500 bytes increase
        mock_counter2.bytes_recv = 4500  # 2500 bytes increase
        
        # First call returns the first counter
        mock_net_io_counters.return_value = {'eth0': mock_counter1}
        
        # Initialize with a 1-second refresh interval
        net_stats = NetworkStats(refresh_interval=1.0)
        
        # Second call returns the second counter
        mock_net_io_counters.return_value = {'eth0': mock_counter2}
        net_stats._get_counters()
        
        # Calculate speed
        upload_speed, download_speed = net_stats._calculate_speed('eth0')
        
        # With a 1-second interval, should match the byte difference
        assert upload_speed == 1500
        assert download_speed == 2500
