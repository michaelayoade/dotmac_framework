"""DotMac Packages Root"""

# This file makes the dotmac namespace package work properly
__path__ = __import__('pkgutil').extend_path(__path__, __name__)