# Acer 8730g

Examining the flash ROM write protection scheme implemented on the Acer 8730g laptop.

## Preface
Having suffered a hardware failure on one of my laptops, I dug out a spare which had been collecting dust for some years. This machine had actually been donated to me, but instead of finding it a good home as usual I've hung on to it as it has a decent keyboard/screen/memory configuration and the CPU is okay for the period (note: the disk in it is terrible however even for the period, a slow 5k, there are 2 SATA ports so a spare SSD has helped).

One installation of Debian later and a little configuration, the majority of the hardware is working. The advantage of such an old machine is that nearly all the hardware will have had drivers developed by now! :grin: One problem however is that having received this machine so late in it's life it hadn't had any firmware updates. A major pain when using x86 machines (Intel/AMD) is their dependence on the Management Engine (ME, or it's AMD equivalent), it along with other technologies (eg: Intel AMT) provide a fertile ground for those wishing to compromise machines. Once you hit the OEM EOL for a system you are stuck between a rock and hard place in regard to firmware issues. You can have a perfectly functional machine which is a potential security risk due to ageing firmware, and due to the locked down nature of the ME/bootstrap process, left without means to even replace it. There does exist however a few programs which can help in this situation by disabling different aspects of ME (for earlier versions at least), and there are various ways of improving the security of the main firmware (BIOS/(U)EFI) by replacing (aspects) of it with OSS replacements[1][2][3].

Having previously modified a BayTrail tablet's ROM to lobotomise ME, I wanted to experiment with changing the firmware on this machine. In that case modifing the ROM was easy as it was on a daughterboard that could be detached from the mainboard and hooked up to a SPI programmer to read & write the contents. In this case the ROM is on the mainboard which makes programming in system programming more difficult (plus the machine's a pain to disassemble as well), so programming in situ via software is preferable (obviously still need to factor in the case of having to unbrick it manually :wink: ).

The starting point for this is previously released firmware versions, and visiting Acer's website I was disappointed to find that there were no firmware images available for download. Windows 7 drivers yes, firmware no, thanks a bunch Acer. This left the distasteful option of third party sites, where you have absolutely no assurance of the integrity of the file you're trying to download. I managed to find version 1.09 (same as the system), but with no assurance of what it actually was there was no way it was going anywhere near the system. With this in mind and a wish to be able to update the flash ROM from Linux it's time to roll up the sleeve's and peek (or poke, sorry BASIC joke) under the hood.

## Setup
The firmware update comes packaged as a zipfile, so after unpacking it a number of different files are apparent. The update contains software to flash the ROM in both DOS & Windows, and a couple of different ROM images which differ in that one has an additional data section appended to it. Having a DOS executable (**phlash16.exe**) to analyse was handy as the amount of code dedicated to the interface is minimised (generally) so this was selected as the point of attack. 

#### QEMU/FreeDOS
<img src="pics/qemu-1st-run.png" height="33%" width="33%" align="right">
Static analyse can provide insights into the code, but running a binary can provide greater information far faster, so I decided to use QEMU to provide a virtual environment running FreeDOS[4]. With FreeDOS installed and the binary/ROM transfered a test run could be done. The phlash16 program provides a number of different <a href="phlash16-1.6.9.7.exe/phlash16-args.txt">arguments</a> which can be passed to it, and the required parameters can be found in the batch file 'BIOS.bat'. These are 'phlash16 /x /s /c /mode=3 <bios image>'. Running this produces some output which is not exactly useful but is a good start.
<br clear="right"/><br/>

<img src="pics/qemu-debug-example.png" height="33%" width="33%" align="left">Originally I had been intending to use gdb as the debugger to interrogate phlash16, as QEMU/gdb are designed to work together. Unfortunately they are designed to work together when QEMU is operating in 32bit mode, not in real mode, this causes the disassembler to incorrectly interprete instructions which is no use. Switching gdb to 16bit mode causes a protocol error with QEMU, and while some people do appear to have worked around the problem, I had no luck. Scratching my head for a little while I remembered 'debug' which is a command line debugger that has been included in MS-DOS since version 1.00. An extended version is included in FreeDOS, so loading up the phlash16 executable with this provides a simple TUI to examine the program.
<br clear="left"/>

#### Radare2
<img src="pics/radare2-phlash16-entry0.png" height="33%" width="33%" align="right">
So examining the executable with debug is useful and informative, but to get a better understanding of a program my preferred IDA is radare2. It's has it's flaws but it's OSS, which I much prefer to use when possible. It's built on ncurses so is a TUI rather than a GUI (though there is the 'iaito' Qt frontend), with my main complaint of it being that learning the controls is a bit esoteric. On this particular project there is also another problem however in that the address handling is a little borked. Addresses are displayed as realmode 'segment:offset', but any commands use the actual physical address. Worse still, it also has problems handling the call/jmp instructions (as opposed to lcall/ljmp), where it calculates the address to be always in the first segment, and tracing through the code becomes confusing if you don't notice where you've jumped to. :wink: Lastly is project management where radare2 saves it's state to a git repo. which in theory sounds like a good idea, however as this state is monolithic it becomes quite hard to check changes that have been made (especially if you mistype addresses!). You can however load in configuration from plain text files which is what I tend to do.

<br clear="right"/><br/>

##Phlash16
Initial analysis (r2 cmd: aaaa) in radare identifies a number of functions with only the entry point and main function being labeled (which is not surprising). A good place to start when trying to disassemble a program is the user I/O and this is where things started to become interesting. As this is a DOS program it would be expected that the program would use INT 10h to print information to the screen. Searching the program code for '0xcd 0x10' (INT 10h instruction) doesn't produce many results, so the debug commands step over ('p') and step into ('t') were used to identify a section of code that updated the screen. After a few attempts a block was identified that among other things cleared the screen (partial listing below):
```
            ; CALL XREF from fcn.00001476 @ 0x147d(x)
            ; CALL XREF from fcn.000019b4 @ 0x19c3(x)
┌ 427: fcn.0000a6d6 ();
│           ; var int16_t var_eh @ bp-0xe
│           ; var uint32_t var_19h @ bp-0x19
│           ; var uint32_t var_1ah @ bp-0x1a
│           ; var uint32_t var_1ch @ bp-0x1c
│           0000:a6d6      c81e0000       enter 0x1e, 0
│           0000:a6da      33db           xor bx, bx
│           0000:a6dc      8ec3           mov es, bx
│           0000:a6de      6626833e4000.  cmp dword es:[0x40], 0
│           0000:a6e5      7505           jne 0xa6ec
│           ; CODE XREFS from fcn.0000a6d6 @ 0xa78b(x), 0xa7bd(x), 0xa801(x)
│           0000:a6e7      33c0           xor ax, ax
│           0000:a6e9      c9             leave
│           0000:a6ea      cb             retf
            0000:a6eb      90             nop
│           ; CODE XREF from fcn.0000a6d6 @ 0xa6e5(x)
│           0000:a6ec      66c746f20012.  mov dword [var_eh], 0x55101200 ; [0x55101200:4]=-1
│           0000:a6f4      8d46e4         lea ax, [var_1ch]
│           0000:a6f7      16             push ss
│           0000:a6f8      50             push ax
│           0000:a6f9      8d4ef2         lea cx, [var_eh]
│           0000:a6fc      16             push ss
│           0000:a6fd      51             push cx
│           0000:a6fe      6a10           push 0x10
│           0000:a700      9a805c1213     lcall fcn.00018da0           ; RELOC 16 
│           0000:a705      83c40a         add sp, 0xa
│           0000:a708      807ee755       cmp byte [var_19h], 0x55     ; 'U'
│           0000:a70c      0f85d400       jne 0xa7e4
│           0000:a710      c746f20300     mov word [var_eh], 3
│           0000:a715      8d46e4         lea ax, [var_1ch]
│           0000:a718      16             push ss
│           0000:a719      50             push ax
│           0000:a71a      8d4ef2         lea cx, [var_eh]
│           0000:a71d      16             push ss
│           0000:a71e      51             push cx
│           0000:a71f      6a10           push 0x10
│           0000:a721      9a805c1213     lcall fcn.00018da0           ; RELOC 16 
```

##ROM access code


## References
1. https://www.seabios.org/SeaBIOS
2. https://www.tianocore.org/
3. https://www.linuxboot.org/
4. https://www.freedos.org/


