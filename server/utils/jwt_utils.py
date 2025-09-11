import base64
import json
from typing import Optional, Dict, Any


class JWTUtils:
    @staticmethod
    def decode_payload(token: str) -> Optional[Dict[str, Any]]:
        """解析JWT payload，不验证签名（仅提取信息）"""
        try:
            # JWT格式：header.payload.signature
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            # 解码payload部分
            payload = parts[1]
            # 添加padding如果需要
            payload += '=' * (4 - len(payload) % 4)
            decoded_bytes = base64.urlsafe_b64decode(payload)
            return json.loads(decoded_bytes.decode('utf-8'))
        except Exception as e:
            print(f"JWT decode error: {e}")
            return None
    
    @staticmethod
    def extract_user_id(token: str) -> Optional[str]:
        """从JWT中提取user_id"""
        payload = JWTUtils.decode_payload(token)
        if payload and 'user_id' in payload:
            return str(payload['user_id'])
        return None
    
    @staticmethod
    def extract_username(token: str) -> Optional[str]:
        """从JWT中提取username"""
        payload = JWTUtils.decode_payload(token)
        if payload and 'username' in payload:
            return payload['username']
        return None