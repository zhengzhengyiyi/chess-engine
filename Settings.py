depth = 3

# Performance configuration
use_lazy_smp = False  # Disable Lazy SMP for now (causes GUI issues)
num_workers = 4  # Use 4 worker processes for Lazy SMP (adjust based on your CPU cores)
transposition_table_size = 1000000  # Number of entries in shared transposition table
max_cache_size = 100000  # Maximum LRU cache size for material evaluation
enable_aggressive_caching = True  # Enable aggressive caching for performance
