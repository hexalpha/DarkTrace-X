import unittest
from datetime import UTC, datetime, timedelta
import jwt
from fastapi import HTTPException
from app.core.config import Settings
from app.core.security import Principal, Role, create_access_token, decode_access_token


class TokenTests(unittest.TestCase):
    def setUp(self):
        self.settings=Settings(_env_file=None,jwt_secret='isolated-test-key-at-least-thirty-two-bytes')
        self.principal=Principal(user_id='user',tenant_id='tenant',role=Role.ANALYST,email='qa@example.com')

    def test_token_round_trip(self):
        self.assertEqual(decode_access_token(create_access_token(self.principal,self.settings),self.settings),self.principal)

    def test_invalid_claims_and_algorithms_rejected(self):
        now=datetime.now(UTC)
        base=self.principal.model_dump() | {'sub':'user','exp':now+timedelta(minutes=5),'iss':'darktracex','aud':'darktracex-api'}
        for change in ({'exp':now-timedelta(seconds=1)}, {'iss':'other'}, {'aud':'other'}, {'sub':None}, {'role':'superuser'}):
            token=jwt.encode(base|change,self.settings.jwt_secret.get_secret_value(),algorithm='HS256')
            with self.assertRaises(HTTPException): decode_access_token(token,self.settings)
        for claim in ('sub','exp'):
            data=dict(base);data.pop(claim)
            token=jwt.encode(data,self.settings.jwt_secret.get_secret_value(),algorithm='HS256')
            with self.assertRaises(HTTPException): decode_access_token(token,self.settings)
        token=jwt.encode(base,'',algorithm='none')
        with self.assertRaises(HTTPException): decode_access_token(token,self.settings)
