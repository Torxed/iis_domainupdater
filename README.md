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


Examples
=================

*(assuming you've configured the variables for userid, password, domain and nsserver at the top of the script)*

root@host:# python iis_domainupdater.py 
2012-12-04 23:02:36 - Initated the script
 - Got external IP: 10.133.55.23
 - Imitating login navigation and submission
 - IIS.se is undergoing maintenance, ending the script

root@host:# python iis_domainupdater.py 
2012-12-04 23:21:30 - Initated the script
 - Got external IP: 10.133.55.23
 - Imitating login navigation and submission
 - Imitating update process and fetching ID values
 - Got new ID for example.se, the ID is 1234567
 - Finding current IP at iis.se and imitating update process
 - Skipping update, external IP is the regisitrered IP at iis.se

Running as a CRON job
=================

The script is ment to be run as a cron job every X ammount of time,
in order for the cron job to be able to run this script you need to define some variables:
___customerID___ = ...
___customerPWD___ = ---
___domain___ = ...
___nsserver___ = ...
___externalIP___ = ...

Once those are set, do:
~:# crontab -e

and append:
*/5 * * * * /path/to/scrupt/iis_domainupdater.py

and make sure you've started ( or in this case, restarted, the cron daemon )
~:# /etc/init.d/cron restart
