Description
=================

A script to automate the work you do in order to update your domain at http://iis.se/ for your Swedish domain names.
The script will check your external IP address, navigate through http://iis.se/ and update your desired nameserver for a specific domain.

DynDNS.com and No-Ip.org has similar scripts but gives you the same functionality to IIS.se.

(I know that nameservers should have static IP's and there for never really need this,
but some of us have a hobby-server in the basement, which might get a poweroutage or runs on a ADSL (or both),
and we need to quickly be able to update the IP dynamicly on power-restore or IP changes.)


TODO
=================

The script lacks a lot of error checks and is quite fragile to major changes to the IIS.se website structure.
However the script has some sanity checks and will not spam IIS.se if there's no data to send or if the site is under maintenance.

Add support for multiple nameservers? humm..

The code is UGLY, i'm aware of that, started the work this morning and finished this evening and had time for real work.
So in between having no time and creating this.. well this is what came out, and it works for now :)


Examples
=================

root@host:# python iis_domainupdater.py 
 - Got external IP: 10.22.0.133
 - Imitating login navigation and submission
 - IIS.se is undergoing maintenance, ending the script
