"""Python C6T main file"""

import sys
from .frontend import main

if __name__ == "__main__":
    main.main(sys.argv[1:])
