import proto_socket_django as psd
import proto.messages as pb
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken


class AuthenticationReceiver(psd.FPSReceiver):
    @psd.receive(auth=False)
    def login(self, message: pb.RxLogin):
        user = authenticate(username=message.proto.username, password=message.proto.password)

        if user is None:
            message = pb.TxLoginError(
                pb.TxLoginError.proto(error_text='Invalid login details.', error_code='login-error')
            )
        else:
            refresh = RefreshToken.for_user(user)
            message = pb.TxLoginToken(pb.TxLoginToken.proto(
                token=str(refresh.access_token),
                refresh=str(refresh),
            ))
            self.consumer.token = message.proto.token
        self.consumer.send_message(message)
        self.consumer.authenticate()

    @psd.receive(auth=False)
    def refresh_token(self, message: pb.RxRefreshToken):
        try:
            refresh = RefreshToken(message.proto.refresh_token)
            refresh.set_jti()
            refresh.set_exp()
            refresh.set_iat()
            message = pb.TxLoginToken(pb.TxLoginToken.proto(
                token=str(refresh.access_token),
                refresh=str(refresh),
            ))
            self.consumer.token = message.proto.token
        except Exception as e:
            message = pb.TxRefreshTokenInvalid(pb.TxRefreshTokenInvalid.proto())
        self.consumer.send_message(message)
        self.consumer.authenticate()
