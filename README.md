iis_domainupdater
=================

A script to imitate the work you do to update your domain at http://iis.se/ for your Swedish domain names.



TODO
=================

The script lacks a lot of error checks and is quite fragile to major changes to the IIS.se website structure.
However the script has some sanity checks and will not spam IIS.se if there's no data to send or if the site is under maintenance.

Add support for multiple nameservers? humm..


Examples
=================

root@host:# python iis_domainupdater.py 
 - Got external IP: 10.22.0.133
 - Imitating login navigation and submission
 - IIS.se is undergoing maintenance, ending the script
