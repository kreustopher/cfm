#!/usr/bin/env python3

# build with...
# source /home/chris/c/venvs/pyinstaller/bin/activate.fish ; cd /home/chris/c/projects/filemanager ; rm -rf build dist ; pyinstaller --onefile cfm.py

"""notes {{{
    todo:
        on preview loading screen, show filename then loading for preview
        loading screen for main window
        indicator for scrollup/scrolldownable
        IN THE RARE EVENT SMARTTRUNC IS NOT WORKING, GET RID OF ARTIFACTS THAT APPEAR FROM LONG STRS
        store cds in memory, in a dictionary so I don't have to reload
        add r and R (refresh cd and Refresh All), which just remove from dicts and display()
        If after shell, relposition > max whatever, make it max whatever
        better fish greeting (cfnew)
        self.sortby similar to filter
        indications of filter and self.sortby in new panels
        softlinks are being annoying af. this guy gets it:
            https://bugs.python.org/issue29635
        need to make better pager for items
            smolneed: back_items don't make rel 0 every time it's back; make it what you saw? idk. probably will be same logic for paging in general

    For troubleshooting, look for #troubleshooting

    stdscreen or self.stdscreen? I don't know what to choose...
    better os/shell stuff?
    permissions issues for back files?
    look for:
      # needs update
      filter, add a simple popup box for it!
      recently disabled, do I need?
      cfwow
    done remembers:
      CJK handling
      unicode handling
      added fullpath to @, which is dope
}}} """

import sys, curses, curses.panel, os, subprocess, pathlib, time, unicodedata, threading, uuid, wcwidth # {{{
# from curses import panel
# import easygui, textwrap 
import time
# }}}

# for eachar in sys.argv:
#     print(eachar)
#     input()
if len(sys.argv) > 1:
    os.chdir(sys.argv[1])

# for checking if file is binary or text {{{ 
textchars = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)) - {0x7f})
is_binary_string = lambda bytes: bool(bytes.translate(None, textchars))
# }}}

def dumbtrunc(s, m): # {{{
    cl = 0 # displayed character length
    sl = 0 # string length (ultimate return)
    for ec in s:
        w_or_nah = unicodedata.east_asian_width(ec)
        sl += 1
        cl += 1
        if w_or_nah == 'A':
            cl -= 1
        if w_or_nah == 'W' or w_or_nah == 'F':
            cl += 1
        if cl > m:
            # if w_or_nah == 'W':
                return s[0:sl -1] + '…', m - (cl - sl)
        if cl == m:
            if w_or_nah == 'W':
                return s[0:sl -1] + '……', m - (cl - sl)
            return s[0:sl -1] + '…', m - (cl - sl)
    # output_handler('hiya' + str(m))
    return s[0:sl], m - (cl - sl)
# }}}

def smarttrunc(s, m): # {{{
    # s is string (filename), m is maxlength
    cl = 0 # displayed character length
    sl = 0 # string length (ultimate return)
    for ec in s:
        sl += 1
        cl += wcwidth.wcswidth(ec)
        if cl > m:
                return s[0:sl -1] + '…', m - (cl - sl)
        if cl == m:
            if wcwidth.wcswidth(ec) == 2:
                return s[0:sl -1] + '……', m - (cl - sl)
            return s[0:sl -1] + '…', m - (cl - sl)
    # output_handler('hiya' + str(m))
    return s[0:sl], m - (cl - sl)
# }}}

def get_filesize(bytesize, suffix="B"): # {{{
    # bytesize = float(bytesize)
    for unit in (" ", " K", " M", " G", " T", " P", " E", " Z"):
    # for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(bytesize) < 1024:
            return f"{int(bytesize)}{unit}{suffix}"
            # return f"{bytesize:3.1f}{unit}{suffix}"
        bytesize /= 1024
    return f"{int(bytesize)}Yi{suffix}"
    # return f"{bytesize:.1f}Yi{suffix}"
# }}}

def refresh_dictionary(self, cd, sortby, dtype, uid): # {{{

    cd_prefix = os.path.dirname(os.path.abspath(cd))
    cd_dirs = []
    cd_files = []
    cd_else = []

    if dtype == 'preview':
        try:
            for entry in os.scandir(cd):
                if self.latestuuid != uid:
                    return
                try:
                    if entry.is_dir():
                        cd_dirs.append(entry.name)
                    if entry.is_file():
                        cd_files.append(entry.name)
                        # print(entry.name)
                except:
                    pass
        except:
            return

    else:
        for entry in os.scandir(cd):
            try:
                if entry.is_dir():
                    cd_dirs.append(entry.name)
                if entry.is_file():
                    cd_files.append(entry.name)
                    # print(entry.name)
            except:
                output_handler('WOAH!')
                pass

    cd_all_meta = []
    for eachd in cd_dirs:
        if dtype == 'preview':
                    if self.latestuuid != uid:
                        return

        onlyfiles = 0
        try:
            for entry in os.scandir(os.path.join(cd,eachd)):
                onlyfiles += 1
        except Exception as e:
            onlyfiles = "ERR"
            output_handler(e)
            pass

        try:
            cd_all_meta.append({
                'name':eachd
                ,'createdate':os.path.getctime(eachd)
                ,'moddate':os.path.getmtime(eachd)
                ,'type':'dir'
                ,'files_or_size':onlyfiles
                })
        except:
            cd_all_meta.append({
                'name':eachd
                ,'createdate':9999999999999999999999
                ,'moddate':9999999999999999999999
                ,'type':'dir'
                ,'files_or_size':onlyfiles
                })

    for eachf in cd_files:
        if dtype == 'preview':
                    if self.latestuuid != uid:
                        return
        # get human-readable filesize
        try:
            bytesize = os.path.getsize(eachf)
            humansize = get_filesize(bytesize)
        except:
            bytesize = 0
            humansize = 'ERR'
        try:
            cd_all_meta.append({
                'name':eachf
                ,'createdate':os.path.getctime(eachf)
                ,'moddate':os.path.getmtime(eachf)
                ,'type':'file'
                ,'files_or_size':humansize
                })
        except:
            cd_all_meta.append({
                'name':eachf
                ,'createdate':9999999999999999999999
                ,'moddate':9999999999999999999999
                ,'type':'file'
                ,'files_or_size':humansize
                })
        # output_handler(humansize)
    
    sorted_all_meta_name = sorted(cd_all_meta, key=lambda x: (x["type"],x["name"]))
    sorted_all_meta_create = sorted(cd_all_meta, key=lambda x: (x["type"],x["createdate"]))
    sorted_all_meta_mod = sorted(cd_all_meta, key=lambda x: (x["type"],x["moddate"]))
    
    # format of these is key = name, value = [type(dir/file),selected(Bool)]
    dictlist_cd_files_ready_sorted_name = {}
    dictlist_cd_files_ready_sorted_create = {}
    dictlist_cd_files_ready_sorted_mod = {}
    for i in range(0,len(sorted_all_meta_name)):
        # this is dictlist_cd_files_ready_sorted_name["dir/filename"]
        dictlist_cd_files_ready_sorted_name[sorted_all_meta_name[i]["name"]] = [sorted_all_meta_name[i]["type"],False,sorted_all_meta_name[i]["files_or_size"]]

        # dictlist_cd_files_ready_sorted_name.append(sorted_all_meta_name[i]["name"])
    for i in range(0,len(sorted_all_meta_create)):
        dictlist_cd_files_ready_sorted_create[sorted_all_meta_name[i]["name"]] = [sorted_all_meta_name[i]["type"],False,sorted_all_meta_name[i]["files_or_size"]]
        # dictlist_cd_files_ready_sorted_create.append(sorted_all_meta_create[i]["name"])
    for i in range(0,len(sorted_all_meta_mod)):
        dictlist_cd_files_ready_sorted_mod[sorted_all_meta_name[i]["name"]] = [sorted_all_meta_name[i]["type"],False,sorted_all_meta_name[i]["files_or_size"]]
        # dictlist_cd_files_ready_sorted_mod.append(sorted_all_meta_name[i]["name"])

#     # old n simple {{{
#     if sortby == 'name':
#         return dictlist_cd_files_ready_sorted_name
#     elif sortby == 'create':
#         return dictlist_cd_files_ready_sorted_create
#     elif sortby == 'mod':
#         return dictlist_cd_files_ready_sorted_mod
#     else:
#         return dictlist_cd_files_ready_sorted_name
#     pass
# # }}}

    if sortby == 'name':
        requested_dict = dictlist_cd_files_ready_sorted_name
    elif sortby == 'create':
        requested_dict = dictlist_cd_files_ready_sorted_create
    elif sortby == 'mod':
        requested_dict = dictlist_cd_files_ready_sorted_mod
    else:
        requested_dict = dictlist_cd_files_ready_sorted_name

    if dtype == 'main':
        self.dict_currentlist = requested_dict

    elif dtype == 'back':
        self.dict_backlist = requested_dict

    elif dtype == 'preview':
        self.dict_previewlist = requested_dict
# }}}

def go_in(self, cd): # {{{
    try:
        if os.path.isfile(cd):
            output_handler('uhh!')
            with suspend_curses():
                open_file(self)
            return "don't_refresh"
            # # refresh only if launching can change things!! see other suspend_curses
        else:

            os.chdir(cd)
            cd = os.getcwd()
            refresh_dictionary(self, os.getcwd(), self.sortby, 'main', "")
    except Exception as e:
        output_handler(f'ERROR:, {e}')
        return 'failed'
        pass
        
# }}}

def go_back(): # {{{
    # wasdir = cd
    os.chdir('..')
    # return wasdir
    # pl_error = {
    #         'cd':self.cd
    #         ,'sort':'name'
    #         }
    # raise ValueError(pl_error)
# }}}

class suspend_curses(): # {{{
    """Context Manager to temporarily leave curses mode"""

    def __enter__(self):
        curses.endwin()

    def __exit__(self, exc_type, exc_val, tb):
        newscr = curses.initscr()
        # newscr.addstr('Newscreen is %s\n' % newscr)
        newscr.refresh()
        curses.doupdate()
# }}}

def open_file(self): # {{{
    with open('/tmp/wowdude', 'w') as tmp_fish_cmd:
        ## for bash...
        # tmp_fish_cmd.write(f"export cfm='{cleanval}'\n")
        cleanval = os.path.join(os.getcwd(),self.displayed_items[self.relposition][1].replace("'","\\'"))
        tmp_fish_cmd.write(f"set -U cfm '{cleanval}'\n")
        tmp_fish_cmd.write(f"less -i $cfm")
    subprocess.Popen(['fish /tmp/wowdude'],shell=True).wait()
    # quit() # lol whatever dude
    # }}}

def launch_shell_old(self): # {{{
    subprocess.Popen(['fish','-c',f'cd {os.getcwd()};reset;fish'],env={'TERM':'xterm','cfm':''}).wait()
    # pl_error = {
    #         'cd':self.cd
    #         ,'sort':'name'
    #         }
    # raise ValueError(pl_error)
    # }}}

def launch_shell(self): # {{{
    selected_values = []

    with open('/tmp/wowdude', 'w') as tmp_fish_cmd:
        tmp_fish_cmd.write(f"rm /tmp/wowdude\n")
        tmp_fish_cmd.write(f'cd {os.getcwd()}\n')
        tmp_fish_cmd.write(f"reset\n")
        # tmp_fish_cmd.write(f"set -x cfm\n")
        tmp_fish_cmd.write(f"set -g --erase cfm\n") # maybe don't do -U?
        tmp_fish_cmd.write(f"set -U --erase cfm\n") # maybe don't do -U?
        tmp_fish_cmd.write(f"fish")

    subprocess.Popen(['fish /tmp/wowdude'],shell=True).wait()
    # pl_error = {
    #         'cd':self.cd
    #         ,'sort':'name'
    #         }
    # raise ValueError(pl_error)
# }}}

def launch_shell_with_args(self): # {{{
    selected_values = []
    for key in self.dict_currentlist:
        if self.dict_currentlist[key][1] == True:
            selected_values.append(key)

    # # for bash, do this...:
        # tmp_fish_cmd.write(f"export cfm=\n")
    #     cleanval = ""
    #     cleanls = []
    #     for eachval in selected_values:
    #         tmpval = os.path.join(os.getcwd(),eachval.replace("'","\\'"))
    #         tmpval = "'" + tmpval + "'"
    #         cleanls.append(tmpval)
    #     cleanval = " ".join(cleanls)
        # tmp_fish_cmd.write(f"export cfm=$(ls {cleanval})\n") # maybe don't do -U?

    with open('/tmp/wowdude', 'w') as tmp_fish_cmd:
        # tmp_fish_cmd.write(f"rm /tmp/wowdude\n")
        tmp_fish_cmd.write(f'cd {os.getcwd()}\n')
        tmp_fish_cmd.write(f"reset\n")
        # tmp_fish_cmd.write(f"set -x cfm\n")
        tmp_fish_cmd.write(f"set -g --erase cfm\n") # maybe don't do -U?
        tmp_fish_cmd.write(f"set -U --erase cfm\n") # maybe don't do -U?
        cleanval = ""
        cleanls = []
        for eachval in selected_values:
            # cleanval = eachval.replace("'","\\'")
            cleanval = os.path.join(os.getcwd(),eachval.replace("'","\\'"))
            tmp_fish_cmd.write(f"set -Ua cfm '{cleanval}'\n") # maybe don't do -U?
            # tmp_fish_cmd.write(f"set -x cfm $cfm '{cleanval}'\n") # maybe don't do -U?
        cleanval = " ".join(cleanls)
        tmp_fish_cmd.write(f'export fish_greeting="$fish_greeting\n\nselected items are \\$cfm"\n') # cfnew
        # tmp_fish_cmd.write(f'export fish_greeting="$fish_greeting\n$(echo $cfm)"\n') # cfnew
        tmp_fish_cmd.write(f"fish")

    subprocess.Popen(['fish /tmp/wowdude'],shell=True).wait()
    # pl_error = {
    #         'cd':self.cd
    #         ,'sort':'name'
    #         }
    # raise ValueError(pl_error)
# }}}

def xdg(self, buttonpressed): # {{{
    # subprocess.call(['nvim','/tmp/hi'])
    # subprocess.Popen('nvim', stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    # print(chr(27) + "[2J")
    subprocess.call(['export','mypythonargs=',args,'fish','-c','reset;fish'])
    for eachls in npy_ls:
        eachls.display()
    pass
    pl_error = {
            'cd':self.cd
            ,'sort':'name'
            }
    raise ValueError(pl_error)
# }}}

def output_handler(message): # {{{
    try:
        with open('/tmp/fm_cur_output_handler', 'a') as open_log:
            open_log.write(f"{message}\n")
    except:
        with open('/tmp/fm_cur_output_handler', 'a') as open_log:
            open_log.write(f"Well, there's something fucked with your message\n")

# }}}

def set_sizes_and_positions(self): # {{{
    self.max_y, self.max_x = self.stdscreen.getmaxyx()
    self.max_y += -3
    # Add an error here if self.max_y is less than 1
    self.max_x_back = int(self.max_x * (2 / 15)) -3 # was 2/10
    self.max_x_main = int(self.max_x * (6 / 15)) -4 # pad 2 between them
    self.max_x_right = self.max_x - self.max_x_back - self.max_x_main -7
#CONNECTED
# }}}

class Menu(object):
    def __init__(self, stdscreen):

        # init VERY {{{
        self.stdscreen = stdscreen
        self.dict_currentlist = {}
        self.dict_backlist = {}
        self.dict_previewlist = {}
        self.threads = {}
        self.latestuuid = ""
        self.sortby = 'name'
        self.th = threading.Thread()
        refresh_dictionary(self, os.getcwd(), self.sortby, 'main', "")
        refresh_dictionary(self, '..', self.sortby, 'back', "")
        self.filter = ""
        self.vfilter = "6f8312f4-0f0d-44f8-a81e-11631ebb7d11 be943147-d7a4-4f07-908c-b60e8644f3f2 31d1e686-5b2a-41ed-ab80-2ad75238a4a3"
        set_sizes_and_positions(self)
        # }}}

        # init panels {{{ 
        self.window_back = stdscreen.subwin(1, 1)
        self.window = stdscreen.subwin(1, self.max_x_back + 3)
        self.windowpreview = stdscreen.subwin(1, self.max_x_main + self.max_x_back + 5)
        self.windowcd = stdscreen.subwin(0, self.max_x_back + 3)
        #CONNECTED
        self.window.immedok(True) # automatically refreshes! #cfwow ; implement elsewhere
        self.window_back.immedok(True) # automatically refreshes! #cfwow ; implement elsewhere
        self.windowcd.immedok(True) # automatically refreshes! #cfwow ; implement elsewhere
        self.windowpreview.immedok(True) # automatically refreshes! #cfwow ; implement elsewhere
        self.window.keypad(1) # allows arrow keys to be used
        self.panelcd = curses.panel.new_panel(self.windowcd)
        self.panel = curses.panel.new_panel(self.window)
        self.panel_back = curses.panel.new_panel(self.window_back)
        self.panel_preview = curses.panel.new_panel(self.windowpreview)
        self.panelcd.hide()
        self.panel.hide()
        self.panel_back.hide()
        self.panel_preview.hide()
        curses.panel.update_panels()
        # }}}

        # init color profiles {{{
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_WHITE, -1)
        curses.init_pair(2, curses.COLOR_MAGENTA, -1)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_MAGENTA)
        curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(6, -1, curses.COLOR_RED)
        try:
            curses.init_pair(7, curses.COLOR_BLACK, 10)
        except:
            curses.init_pair(7, curses.COLOR_BLACK, 7)
        curses.init_pair(8, 10, -1)
        curses.init_pair(9, curses.COLOR_BLACK, curses.COLOR_YELLOW)
        #(#A50)
        self.window.bkgd(curses.color_pair(1))
        self.window_back.bkgd(curses.color_pair(1))
        self.windowpreview.bkgd(curses.color_pair(1))
        # }}}

        # init cursor positions {{{
        self.relposition = 0 # where your cursor is brah
        self.relposition_old = 0
        # }}}
        self.start = 0
        self.end = self.max_y
        # self.display() # this is auto-called for some reason. Uncomment this if you see failures. #troubleshooting

    def get_main_items(self, start, end): # {{{
        self.items = [[key,key] for key in self.dict_currentlist if self.filter in key and self.vfilter not in key]
        self.filter = ""
        self.vfilter = "6f8312f4-0f0d-44f8-a81e-11631ebb7d11 be943147-d7a4-4f07-908c-b60e8644f3f2 31d1e686-5b2a-41ed-ab80-2ad75238a4a3"

        # smart shorten (need to make better to show extension)
        #CONNECTED
        for i in range(len(self.items)):
            filename = self.items[i][0]
            files_or_size = self.dict_currentlist[filename][2]
            # if type(files_or_size) == type([]):
            #     files_or_size = len(files_or_size)
            files_or_size = ' ' + str(files_or_size)
            max_x_here = self.max_x_main - len(files_or_size)
            filename, remainder = smarttrunc(filename, max_x_here) 

            output_handler(self.max_x_main)
            filename = filename.ljust(remainder, " ")
            filename += files_or_size
            output_handler(filename + str(self.max_x_main))

            self.items[i][0] = filename

        self.start = start
        self.end = end
        self.displayed_items = self.items[self.start:self.end]
        # }}}

    def get_preview(self, uid): # {{{
        self.windowpreview.clear()
        preview = ["Loading..."]
        self.windowpreview.addstr(1, 0, '\n'.join(preview), curses.color_pair(9))

        try:
            filename = self.displayed_items[self.relposition][1]
        except:
            preview = ["Empty or Inaccessible"]
            self.windowpreview.addstr(1, 0, '\n'.join(preview), curses.color_pair(6))
            return

        # Show list of files/directories
        da_files = self.dict_currentlist[filename][2]
        if da_files == 'ERR' or da_files == None:
            da_files = 0
        if self.dict_currentlist[filename][0] == 'dir' and da_files > 0:
            preview = []
            refresh_dictionary(self, filename, self.sortby, 'preview', uid,)
            self.get_previewdir(0, self.max_y)

            preview = []
            for index, item in enumerate(self.displayed_previewitems):
                if self.dict_previewlist[item[1]][0] == 'dir':
                    mode = curses.color_pair(2)
                    if index == self.relpreviewposition:
                        mode = curses.color_pair(3)
                if self.dict_previewlist[item[1]][0] == 'file':
                    mode = curses.A_NORMAL
                    if index == self.relpreviewposition:
                        mode = curses.A_REVERSE
                preview.append([1 + index, 0, item[0], mode])
            if len(preview) > 0:
                self.windowpreview.clear()
                for eachp in preview:
                    self.windowpreview.addstr(eachp[0], eachp[1], eachp[2], eachp[3]) # this 1 + index places the item up/down. The second "1" places it left/right!

        if self.dict_currentlist[filename][0] == 'file':
            preview = []

            try:
                if is_binary_string(open(filename, 'rb').read(1024)) == False:
                    with open(filename, 'r') as f: 
                        chars = f.read(100)
                        if len(chars) > 0:
                            preview.append(chars)
                        else:
                            preview.append("[Empty File]")
                            # this is throwing an error with some text files but ends up working. Why?
                        self.windowpreview.clear()
                        self.windowpreview.addstr(1, 0, filename, curses.color_pair(5))
                        filename_short, remainder = smarttrunc(filename, self.max_x_right) 
                        add_ind = 0
                        if len(filename_short) < len(filename):
                            add_ind = int(len(filename) / len(filename_short))
                        self.windowpreview.addstr(3 + add_ind, 0, "Preview:", curses.color_pair(8))
                        self.windowpreview.addstr(5 + add_ind, 0, "\n".join(preview), curses.A_NORMAL)
                else:
                    preview.append("Binary File")
                    self.windowpreview.clear()
                    self.windowpreview.addstr(1, 0, filename, curses.color_pair(5))
                    filename_short, remainder = smarttrunc(filename, self.max_x_right) 
                    add_ind = 0
                    if len(filename_short) < len(filename):
                        add_ind = int(len(filename) / len(filename_short))
                    self.windowpreview.addstr(3 + add_ind, 0, "Preview:", curses.color_pair(8))
                    self.windowpreview.addstr(5 + add_ind, 0, "\n".join(preview), curses.color_pair(6))
            except Exception as e:
                pass
                # self.windowpreview.addstr(1, 0, "Inaccessible", curses.color_pair(6))
            pass
        if preview == ['Loading...']:
            preview = ["Empty or Inaccessible"]
            self.windowpreview.addstr(1, 0, '\n'.join(preview), curses.color_pair(6))
    # }}}

    def get_previewdir(self, start, end): # {{{
        self.previewitems = [[key,key] for key in self.dict_previewlist]
        #CONNECTED
        for i in range(len(self.previewitems)):
            filename = self.previewitems[i][0]
            filename, remainder = smarttrunc(filename, self.max_x_right) 
            filename = filename.ljust(remainder, " ")

            self.previewitems[i][0] = filename

        self.previewstart = start
        self.previewend = end

        self.relpreviewposition = 0

        # find where parent dir is, highlight and set previewstart/previewend
        for index, item in enumerate(self.previewitems):
            if item[1] == os.path.basename(os.getcwd()):
                self.relpreviewposition = index
                # self.relpreviewposition = index
                if index > self.max_y:
                    self.previewstart = index
                    self.previewend = self.previewstart + self.max_y
                    self.relpreviewposition = 0
                    if self.previewstart + self.max_y > len(self.previewitems):
                        self.previewend = len(self.previewitems)
                        self.previewstart = self.previewend - self.max_y
                        self.relpreviewposition = index - self.previewstart
        self.displayed_previewitems = self.previewitems[self.previewstart:self.previewend] #updateme
    # }}}

    def get_back_items(self, start, end): # {{{
        self.back_items = [[key,key] for key in self.dict_backlist]
        # smart shorten (need to make better to show extension)
        #CONNECTED
        for i in range(len(self.back_items)):
            filename = self.back_items[i][0]
            filename, remainder = smarttrunc(filename, self.max_x_back) 
            filename = filename.ljust(remainder, " ")

            self.back_items[i][0] = filename

        self.backstart = start
        self.backend = end

        self.relbackposition = 0

        # find where parent dir is, highlight and set backstart/backend
        for index, item in enumerate(self.back_items):
            if item[1] == os.path.basename(os.getcwd()):
                self.relbackposition = index
                # self.relbackposition = index
                if index > self.max_y:
                    self.backstart = index
                    self.backend = self.backstart + self.max_y
                    self.relbackposition = 0
                    if self.backstart + self.max_y > len(self.back_items):
                        self.backend = len(self.back_items)
                        self.backstart = self.backend - self.max_y
                        self.relbackposition = index - self.backstart
        self.displayed_back_items = self.back_items[self.backstart:self.backend] #updateme
        # }}}

    def navigate(self, n): # {{{
        self.relposition += n
        if self.relposition < 0:
            self.relposition = 0
            if self.start > 0:
                self.start += n
                self.end += n
                # new, good for multijumps
                if self.start < 0:
                    self.start = 0
                    self.end = self.max_y
                self.displayed_items = self.items[self.start:self.end]

        elif self.relposition >= len(self.displayed_items):
            self.relposition = len(self.displayed_items) -1
            if self.end < len(self.items):
                self.start += n
                self.end += n
                # new, good for multijumps
                if self.end > len(self.items):
                    self.end = len(self.items)
                    self.start = len(self.items) - self.max_y
                self.displayed_items = self.items[self.start:self.end]

        # Close get.previews blah blah blah.
        uid = uuid.uuid4()
        self.latestuuid = uid
        self.threads[uid] = (threading.Thread(target=self.get_preview, args=(uid,))) # to the above, I think this is why. this seems to work this way
        self.threads[uid].start()
        for key, thread in self.threads.items():
            if key != uid:
                thread.join()
        # self.get_preview() # to the above, I think this is why. this seems to work this way
    # }}}

    def display(self): # {{{
        self.panelcd.top()
        self.panelcd.show()
        self.panel.top()
        self.panel.show()
        self.panel_back.top()
        self.panel_back.show()
        self.panel_preview.top()
        self.panel_preview.show()

        self.windowcd.clear()
        self.windowcd.addstr(0, 0, os.getcwd(), curses.A_NORMAL)

        refresh_dictionary(self, os.getcwd(), self.sortby, 'main', "")
        self.window.clear()
        self.get_main_items(self.start, self.end)

        refresh_dictionary(self, '..', self.sortby, 'back', "")
        self.window_back.clear()
        self.get_back_items(0, self.max_y)

        self.windowpreview.clear()

        # Close get.previews blah blah blah.
        uid = uuid.uuid4()
        self.latestuuid = uid
        self.threads[uid] = (threading.Thread(target=self.get_preview, args=(uid,)))
        self.threads[uid].start()
        for key, thread in self.threads.items():
            if key != uid:
                thread.join()

        # window_back
        for index, item in enumerate(self.displayed_back_items):
            if self.dict_backlist[item[1]][0] == 'dir':
                mode = curses.color_pair(2)
                if index == self.relbackposition:
                    mode = curses.color_pair(3)
            if self.dict_backlist[item[1]][0] == 'file':
                mode = curses.A_NORMAL
                if index == self.relbackposition:
                    mode = curses.A_REVERSE

            # displayed (index 0)
            # msg = "%d. %s" % (index, item[0])
            self.window_back.addstr(1 + index, 0, item[0], mode) # this 1 + index places the item up/down. The second "1" places it left/right!

        while True:

            # Window1
            for index, item in enumerate(self.displayed_items):
                if self.dict_currentlist[item[1]][0] == 'dir':
                    mode = curses.color_pair(2)
                    if index == self.relposition:
                        mode = curses.color_pair(3)
                    if self.dict_currentlist[item[1]][1] == True:
                        mode = curses.color_pair(4)
                        if index == self.relposition:
                            mode = curses.color_pair(7)
                if self.dict_currentlist[item[1]][0] == 'file':
                    mode = curses.A_NORMAL
                    if index == self.relposition:
                        mode = curses.A_REVERSE
                    if self.dict_currentlist[item[1]][1] == True:
                        mode = curses.color_pair(5)
                        if index == self.relposition:
                            mode = curses.color_pair(7)

                self.window.addstr(1 + index, 0, item[0], mode) # this 1 + index places the item up/down. The second "1" places it left/right!

            if self.displayed_items == []:
                self.window.addstr(1, 0, "Empty or Inaccessible!!", curses.color_pair(6)) # this 1 + index places the item up/down. The second "1" places it left/right!
            else:
                pass
                # output_handler(type(self.displayed_items))
                # output_handler(self.displayed_items)
            key = self.window.getch()

            if key in [ord("\n"), ord('h'), curses.KEY_LEFT]:
                wasdir = os.getcwd()
                self.relposition = self.relbackposition # where your cursor is brah
                # temporary while it loads...
                self.displayed_items = self.displayed_back_items
                self.relposition_old = 0
                self.start = self.backstart
                self.end = self.backend
                go_back()
                # removed refreshers from here. let's see...
                self.display()
                pass

            if key in [curses.KEY_ENTER, ord("\n"), ord('l'), curses.KEY_RIGHT]:
                if self.displayed_items != []:
                    return_message = go_in(self, self.displayed_items[self.relposition][1])
                else:
                    return_message = 'failed'

                if return_message != 'failed' and return_message != "don't_refresh":
                    self.relposition = 0 # where your cursor is brah
                    self.relposition_old = 0
                    self.start = 0
                    self.end = self.max_y
                    self.display()

            elif key == ord(' '):
                if self.dict_currentlist[self.displayed_items[self.relposition][1]][1] == True:
                    self.dict_currentlist[self.displayed_items[self.relposition][1]][1] = False
                else:
                    self.dict_currentlist[self.displayed_items[self.relposition][1]][1] = True

            elif key == ord(':'):
                with suspend_curses():
                    launch_shell(self)
                # refresh
                self.display()

            elif key == ord('@'):
                if self.displayed_items == []:
                    with suspend_curses():
                        launch_shell(self)

                else:
                    self.dict_currentlist[self.displayed_items[self.relposition][1]][1] = True
                    with suspend_curses():
                        launch_shell_with_args(self)
                self.display()

            elif key == curses.KEY_UP or key == ord('k'):
                self.navigate(-1)

            elif key == curses.KEY_DOWN or key == ord('j'):
                self.navigate(1)

            elif key == ord('d'):
                self.navigate(5)

            elif key == ord('u'):
                self.navigate(-5)

            elif key == ord('q'):
                exit()
                quit()

            # need another key for help, and ? is my vfilter...
            elif key == ord('H') or key == ord('?'):
                with suspend_curses():
                    os.system('clear')
                    print("Help screen")
                    print("Arrows/Vim bindings to move")
                    print("")
                    print("/        to filter")
                    print("\\       to exclusion filter")
                    print("<space>  to select items")
                    print(":        to launch shell at cd")
                    print("@        to launch shell at cd with $cfm as selected items (full links)")
                    input()
                    os.system('clear')

            elif key == ord('/'):
                with suspend_curses():
                    os.system('clear')
                    print("Filter... [leave blank to cancel]")
                    self.filter = input()
                    os.system('clear')
                self.relposition = 0
                self.display()

            elif key == ord('\\'):
                with suspend_curses():
                    os.system('clear')
                    print("Filter (exclude)... [leave blank to cancel]")
                    self.vfilter = input()
                    if self.vfilter == "":
                        self.vfilter = "6f8312f4-0f0d-44f8-a81e-11631ebb7d11 be943147-d7a4-4f07-908c-b60e8644f3f2 31d1e686-5b2a-41ed-ab80-2ad75238a4a3"
                    os.system('clear')
                self.relposition = 0
                self.display()

            elif key == ord('t'):
                self.panel.hide()
                # self.get_preview()

        else:
            output_handler('aaaah!!!!!')

    # }}}

class MyApp(object): # {{{
    def __init__(self, stdscreen):
        self.screen = stdscreen
        curses.curs_set(0)

        main_menu = Menu(self.screen)
        main_menu.display()
# }}}

if __name__ == "__main__":
    curses.wrapper(MyApp)
