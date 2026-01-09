"""
WeChat API integration utilities
"""
import requests
import json
import certifi
import os
from django.conf import settings
from django.core.cache import cache


class WeChatAPI:
    """WeChat API client for mini-program integration"""
    
    def __init__(self):
        self.appid = settings.WECHAT_APPID
        self.appsecret = settings.WECHAT_APPSECRET
        self.base_url = "https://api.weixin.qq.com"
        # 使用certifi提供的CA证书包路径，确保使用最新的证书
        self.verify_ssl = os.getenv('WECHAT_VERIFY_SSL', certifi.where())
        
        # Validate configuration
        if not self.appid or not self.appsecret:
            raise ValueError(
                "WeChat configuration is missing. Please set WECHAT_APPID and WECHAT_APPSECRET in environment variables."
            )
    
    def code2session(self, js_code):
        """
        Exchange js_code for session_key and openid
        """
        url = f"{self.base_url}/sns/jscode2session"
        params = {
            'appid': self.appid,
            'secret': self.appsecret,
            'js_code': js_code,
            'grant_type': 'authorization_code'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10, verify=self.verify_ssl)
            data = response.json()
            
            if 'errcode' in data and data['errcode'] != 0:
                errcode = data.get('errcode')
                errmsg = data.get('errmsg', 'Unknown error')
                
                # Provide more helpful error messages for common errors
                if errcode == 40013:
                    error_msg = f"Invalid AppID. Please check WECHAT_APPID configuration. Error: {errmsg}"
                elif errcode == 40125:
                    error_msg = f"Invalid AppSecret. Please check WECHAT_APPSECRET configuration. The AppSecret may have been reset in WeChat platform. Error: {errmsg}"
                elif errcode == 40029:
                    error_msg = f"Invalid js_code. The code may have expired or been used. Error: {errmsg}"
                elif errcode == 45011:
                    error_msg = f"API frequency limit exceeded. Please try again later. Error: {errmsg}"
                else:
                    error_msg = f"WeChat API error (code: {errcode}): {errmsg}"
                
                return None, error_msg
            
            # Check if openid is missing (should not happen if request succeeded)
            if 'openid' not in data:
                return None, "WeChat API returned invalid response: missing openid"
            
            return {
                'openid': data.get('openid'),
                'session_key': data.get('session_key'),
                'unionid': data.get('unionid')
            }, None
            
        except requests.RequestException as e:
            return None, f"Network error: {str(e)}"
        except json.JSONDecodeError:
            return None, "Invalid response from WeChat API"
    
    def get_phone_number(self, code, session_key):
        """
        Get phone number from WeChat using phone code
        """
        url = f"{self.base_url}/wxa/business/getuserphonenumber"
        
        # Get access token
        access_token = self.get_access_token()
        if not access_token:
            return None, "Failed to get access token"
        
        data = {
            'code': code
        }
        
        try:
            response = requests.post(
                f"{url}?access_token={access_token}",
                json=data,
                timeout=10,
                verify=self.verify_ssl
            )
            result = response.json()
            
            if result.get('errcode') != 0:
                return None, f"WeChat API error: {result.get('errmsg', 'Unknown error')}"
            
            phone_info = result.get('phone_info', {})
            return {
                'phone_number': phone_info.get('phoneNumber'),
                'pure_phone_number': phone_info.get('purePhoneNumber'),
                'country_code': phone_info.get('countryCode')
            }, None
            
        except requests.RequestException as e:
            return None, f"Network error: {str(e)}"
        except json.JSONDecodeError:
            return None, "Invalid response from WeChat API"
    
    def get_access_token(self):
        """
        Get WeChat access token with caching
        """
        cache_key = f"wechat_access_token_{self.appid}"
        access_token = cache.get(cache_key)
        
        if access_token:
            return access_token
        
        url = f"{self.base_url}/cgi-bin/token"
        params = {
            'grant_type': 'client_credential',
            'appid': self.appid,
            'secret': self.appsecret
        }
        
        try:
            response = requests.get(url, params=params, timeout=10, verify=self.verify_ssl)
            data = response.json()
            
            if 'access_token' in data:
                access_token = data['access_token']
                expires_in = data.get('expires_in', 7200)
                # Cache for slightly less time to avoid expiration issues
                cache.set(cache_key, access_token, expires_in - 300)
                return access_token
            
            return None
            
        except (requests.RequestException, json.JSONDecodeError):
            return None
    
    def get_user_info(self, encrypted_data, iv, session_key):
        """
        Get user info from WeChat encrypted data
        """
        return self.decrypt_data(encrypted_data, iv, session_key)
    
    def decrypt_data(self, encrypted_data, iv, session_key):
        """
        Decrypt WeChat encrypted data (for user info, phone number, etc.)
        """
        try:
            import base64
            from Cryptodome.Cipher import AES
            
            session_key = base64.b64decode(session_key)
            encrypted_data = base64.b64decode(encrypted_data)
            iv = base64.b64decode(iv)
            
            cipher = AES.new(session_key, AES.MODE_CBC, iv)
            decrypted = cipher.decrypt(encrypted_data)
            
            # Remove padding
            pad = decrypted[-1]
            if isinstance(pad, str):
                pad = ord(pad)
            decrypted = decrypted[:-pad]
            
            return json.loads(decrypted.decode('utf-8')), None
            
        except Exception as e:
            return None, f"Decryption error: {str(e)}"