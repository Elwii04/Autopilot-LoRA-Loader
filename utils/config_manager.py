"""
Configuration Manager for SmartPowerLoRALoader
Handles loading API keys from .env file and configuration management.
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, Dict, Any


class ConfigManager:
    """Manages configuration and API keys for the SmartPowerLoRALoader."""
    
    def __init__(self):
        """Initialize the configuration manager and load .env file."""
        self.root_dir = Path(__file__).parent.parent
        self.env_path = self.root_dir / '.env'
        self.env_example_path = self.root_dir / '.env.example'
        self.data_dir = self.root_dir / 'data'
        self.settings_path = self.data_dir / 'settings.json'
        self.settings: Dict[str, Any] = {}
        
        # Create .env from .env.example if it doesn't exist
        if not self.env_path.exists():
            if self.env_example_path.exists():
                # Copy example file
                import shutil
                shutil.copy(self.env_example_path, self.env_path)
                print(f"[SmartPowerLoRALoader] Created .env file from .env.example at {self.env_path}")
                print(f"[SmartPowerLoRALoader] Please edit .env and add your API keys")
            else:
                # Create default .env
                default_content = """# API Keys for LLM Providers
# Add your API keys below

# Groq API Key (get from: https://console.groq.com)
GROQ_API_KEY=your_groq_api_key_here

# Google Gemini API Key (get from: https://aistudio.google.com/apikey)
GEMINI_API_KEY=your_gemini_api_key_here
"""
                self.env_path.write_text(default_content)
                print(f"[SmartPowerLoRALoader] Created default .env file at {self.env_path}")
                print(f"[SmartPowerLoRALoader] Please edit .env and add your API keys")
        
        # Load environment variables
        if self.env_path.exists():
            load_dotenv(self.env_path)
        else:
            print(f"[SmartPowerLoRALoader] Warning: .env file not found at {self.env_path}")
            print(f"[SmartPowerLoRALoader] Copy .env.example to .env and add your API keys")
        
        # Load persisted settings (non-secret config)
        self._load_settings()
    
    def _load_settings(self):
        """Load persistent settings from data/settings.json if available."""
        if not self.settings_path.exists():
            self.settings = {}
            return
        
        try:
            with open(self.settings_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self.settings = data
                else:
                    self.settings = {}
        except Exception as e:
            print(f"[SmartPowerLoRALoader] Error loading settings.json: {e}")
            self.settings = {}
    
    def _save_settings(self):
        """Persist current settings to disk."""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[SmartPowerLoRALoader] Error saving settings.json: {e}")
    
    def get_groq_api_key(self) -> Optional[str]:
        """
        Get Groq API key from environment.
        
        Returns:
            API key string or None if not set
        """
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key or api_key == 'your_groq_api_key_here':
            return None
        return api_key
    
    def get_gemini_api_key(self) -> Optional[str]:
        """
        Get Gemini API key from environment.
        
        Returns:
            API key string or None if not set
        """
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key or api_key == 'your_gemini_api_key_here':
            return None
        return api_key
    
    @property
    def groq_api_key(self) -> Optional[str]:
        """Property for backward compatibility."""
        return self.get_groq_api_key()
    
    @property
    def gemini_api_key(self) -> Optional[str]:
        """Property for backward compatibility."""
        return self.get_gemini_api_key()
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """Generic accessor for provider API keys."""
        provider = (provider or '').lower()
        if provider == 'groq':
            return self.get_groq_api_key()
        if provider == 'gemini':
            return self.get_gemini_api_key()
        return None
    
    def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """
        Retrieve a configuration value.
        
        Precedence:
        1. Environment variable (uppercased key)
        2. Persisted settings.json value
        3. Provided default
        """
        if not key:
            return default
        
        env_key = key.upper()
        env_value = os.getenv(env_key)
        if env_value not in (None, ''):
            return env_value
        
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any, save: bool = True):
        """
        Persist a configuration value to settings.json.
        
        Args:
            key: Setting name
            value: Value to store (JSON-serializable)
            save: Whether to immediately save to disk
        """
        if not key:
            return
        
        self.settings[key] = value
        if save:
            self._save_settings()
    
    def validate_api_keys(self, provider: str) -> tuple[bool, str]:
        """
        Validate that the required API key is available for a provider.
        
        Args:
            provider: Provider name ('groq' or 'gemini')
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if provider.lower() == 'groq':
            key = self.get_groq_api_key()
            if not key:
                return False, "Groq API key not found. Please set GROQ_API_KEY in .env file"
        elif provider.lower() == 'gemini':
            key = self.get_gemini_api_key()
            if not key:
                return False, "Gemini API key not found. Please set GEMINI_API_KEY in .env file"
        else:
            return False, f"Unknown provider: {provider}"
        
        return True, ""


# Global configuration instance
config = ConfigManager()
