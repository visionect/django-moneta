import simplejson
from pysimplesoap.client import SoapClient

from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.db import models

from moneta import signals, transport


class Transaction(models.Model):
    transactionId = models.CharField(max_length=36)
    created = models.DateTimeField(auto_now_add=True)
    expires = models.DateTimeField()
    token = models.CharField(max_length=10)
    status = models.IntegerField(default=11)

    errorCode = models.IntegerField(blank=True, null=True)
    errorDescription = models.CharField(max_length=250, blank=True)

    reference = models.CharField(max_length=100, blank=True)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    additionalInfo = models.TextField(blank=True)

    class Meta:
        get_latest_by = 'created'

    def _initService(self):
        transport.NSSTransport(settings.MONETA_DBDIR, settings.MONETA_CERT_NAME)
        if getattr(settings, 'MONETA_PRODUCTION', False):
            url = 'https://eterminal.moneta.si/mpay.mgw.public/public.asmx?wsdl'
        else:
            url = 'https://e-pos-t.moneta.si/mpay.mgw.public/public.asmx?wsdl'
        self.soapClient = SoapClient(wsdl=url)

    def getToken(self):
        if self.token == '':
            self._initService()

            token = self.soapClient.GetToken(getattr(settings, 'MONETA_PIN', None), str(self.value) + ' EUR', self.reference, False, 0)

            self.transactionId = token['GetTokenResult']['TransactionId']
            self.token = token['GetTokenResult']['Token']
            self.expires = token['GetTokenResult']['ValidUntil']
            self.errorCode = token['GetTokenResult']['ErrorCode']
            if self.errorCode:
                self.errorDescription = token['GetTokenResult']['ErrorDescription']
            self.save()

        return self.token

    def getStatus(self):
        self._initService()
        s = self.soapClient.GetTransactionStatus(getattr(settings, 'MONETA_PIN', None), self.transactionId)['GetTransactionStatusResult']

        obj = self
        obj.id = None
        obj.created = None

        obj.status = s['Status']
        obj.errorCode = s['ErrorCode']
        if obj.errorCode:
            obj.errorDescription = s['ErrorDescription']
        obj.save()

        return obj

    def cancel(self):
        self._initService()
        result = self.soapClient.CancelTransaction(getattr(settings, 'MONETA_PIN', None), self.transactionId)

        obj = self
        obj.id = None
        obj.created = None

        obj.status = result['CancelTransactionResult']['Status']
        obj.errorCode = result['CancelTransactionResult']['ErrorCode']
        if obj.errorCode:
            obj.errorDescription = result['CancelTransactionResult']['ErrorDescription']
        obj.save()

        return obj

    def save(self, *args, **kwargs):
        if self.id is not None:
            raise SuspiciousOperation("This model is append only!")
        try:
            old = Transaction.objects.filter(transactionId=self.transactionId).latest()
            if old.status != self.status and self.status == 3:
                signals.transaction_done.send(sender=self)
        except Transaction.DoesNotExist:
            pass

        super(Transaction, self).save(*args, **kwargs)

    def delete(self):
        raise SuspiciousOperation("This model is append only!")
