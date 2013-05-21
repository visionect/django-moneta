django-moneta
=============

Django app for Moneta eTerminal API.
Mozzila's NSS library is used for secure communications, because OpenSSL or GnuTLS doesn't work with Moneta's servers.

Requirements
------------

* [Django] 1.3+
* [pysimplesoap] 1.08b+
* [python-nss] 0.12+

Installation
--------------

```pip install django-moneta```

Usage
-----

1. Create NSS database with Mobitel's root CA certificate and your client certificate (you can use certconvert.sh)
2. Edit your settings.py
 * Add `moneta` to `INSTALLED_APPS`
 * set `MONETA_DBDIR` to point to NSS directory you've created in first step
 * set `MONETA_CERT_NAME` to your client certificate name
 * optionally set `MONETA_PIN` if you're using it
 * set `MONETA_PRODUCTION` to `True` when you go to production
3. Use `Transaction` model:

```python
from decimal import Decimal
from moneta.models import Transaction

t = Transaction(value=Decimal('1.23'), reference='areference123')
token = t.getToken()

print "Please call %s to pay." % token

t.getStatus()
print t.status #should be 11 since it was just created

t.cancel()
print t.status #should be 7
```

When transaction is finished `transaction_done` signal is emitted.

TODO
====

* Suport delayed transaction
* Support other API functions

[Django]: http://djangoproject.com/
[pysimplesoap]: https://code.google.com/p/pysimplesoap/
[python-nss]: https://www.mozilla.org/projects/security/pki/python-nss/