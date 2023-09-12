import sys

from textbar_manager import print_value

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python print_utility_value.py <utility>")
        sys.exit(1)

    utility = sys.argv[1]
    value = print_value(utility)
    print(value)