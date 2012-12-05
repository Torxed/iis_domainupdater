Description
=================

A script to automate the work you do in order to update your domain at http://iis.se/ for your Swedish domain names.
The script will check your external IP address, navigate through http://iis.se/ and update your desired nameserver for a specific domain.

http://DynDNS.com and http://No-Ip.org has similar scripts but this script gives you the same functionality towards IIS.se.

(I know that nameservers should have static IP's and there for never really need this,
but some of us have a hobby-server in the basement, which might get a poweroutage or runs on a ADSL (or both),
and we need to quickly be able to update the IP dynamicly on power-restore or IP changes.)


TODO
=================

The script lacks a lot of error checks and is quite fragile to major changes to the IIS.se website structure.
However the script has some sanity checks and will not spam IIS.se if there's no data to send or if the site is under maintenance.

*Important:*
Add TSL/SSL verifications to the certificate from the host,
this to ensure that the certificate from the server is correct before we post any login credentials.
As of now (just to get this working) the socket is a blocking socket (unblocked via a crappy threaded class) and
the socket doesn't bother checking the certificate as long as it can establish a a connection!

Add support for multiple nameservers? humm..

The code is UGLY, i'm aware of that, started the work this morning and finished this evening and had time for real work.
So in between having no time and creating this.. well this is what came out, and it works for now :)


Configuration
=================
You can run the script as is, and you'll be promted for all the values needed.
But if you plan on running this as a cron job (or otherwise as a reoccuring job) i'd suggest (example):
```python
    ___customerID___ = '12345678'
    ___customerPWD___ = r'my%sparse\pwd'
    ___domain___ = 'exempel.se'
    ___nsserver___ = 'ns1.exempel.se'
    ___externalIP___ = None # <- For autodetect
```
__This configuration works with the nameserver setup:__
![My image](https://lh3.googleusercontent.com/-i1cuSLcuxXXAFfCqBAVHhkSEHo5W4lJQ-3Hm1ls9xzrWKlPlpVEtLiHh4eZh3QSKam5H5A5bPU)


Example outputs
=================

*(assuming you've configured the variables for userid, password, domain and nsserver at the top of the script)*

<pre>
root@host:# python iis_domainupdater.py 
2012-12-04 23:02:36 - Initated the script
 - Got external IP: 10.133.55.23
 - Imitating login navigation and submission
 - IIS.se is undergoing maintenance, ending the script
</pre>

<pre>
root@host:# python iis_domainupdater.py 
2012-12-04 23:21:30 - Initated the script
 - Got external IP: 10.133.55.23
 - Imitating login navigation and submission
 - Imitating update process and fetching ID values
 - Got new ID for exempel.se, the ID is 1234567
 - Finding current IP at iis.se and imitating update process
 - Skipping update, external IP is the regisitrered IP at iis.se
</pre>

<pre>
root@host:# python iis_domainupdater.py
2012-12-05 00:25:01 - Initated the script
 - Got external IP: 10.133.55.23
 - External IP matches the last known IP on IIS.se, ending the script
</pre>

Running as a CRON job
=================

1. Follow the configration steps above

2. Once those are set, do:
<pre>~:# crontab -e</pre>

3. and append (to run every 5 minutes):
<pre>*/5 * * * * /path/to/scrupt/iis_domainupdater.py</pre>

4. and make sure you've started ( or in this case, restarted, the cron daemon )
<pre>~:# /etc/init.d/cron restart</pre>
