## ================== Explanation of the different variables ===================
## ==                                                                         ==
## = __customerID__ - It's the customer ID number you've recieved from iis,    =
## =                  normally it's just a 8 digit number, we'll use it as     =
## =                  a username when we authenticate.                         =
## = __customerPWD__ - This is your password belonging to __customerID__       =
## = __domain__ - Which domain are you trying to update? we need this to find  =
## =              the domain-id that iis has given you.                        =
## = __nsserver__ - Which nameserver do you want to update the IP of?          =
## =                normally there should be at least 2 name-servers for each  =
## =                domain, and they should be on different servers so in      =
## =                order for the script to update the correct nameserver,     =
## =                enter the nameserver that this script will run on.         =
## = __externalIP__ - It's as simple as to what is your external IP?           =
## =                  The script will try to determain the extnernal IP for    =
## =                  you but if you want, you can always make it static here. =
## =============================================================================

__customerID__ = None
__customerPWD__ = None # example: r'this\is&a%super;password' escapes %s etc
__domain__ = None
__nsserver__ = None
__externalIP__ = None
__lastknown__ = None