import sys
import os
from shutil import copy, copytree, rmtree
from subprocess import run
from dotenv import load_dotenv

from glob import glob
from binascii import unhexlify
from struct import unpack, pack
from numpy import uint32, frombuffer, int32

from tkinter import Tk, filedialog


key = 0xC7CEB2EE
xor_mask = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x11M19\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x11M19\x11M19\x00\x00\x00\x00\x00\x00\x00\x00\x11M19\x11M19\x11M19\x11M19\x11M19\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x11M19\x11M19\x11M19\x11M19\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x11M19\x00'
disable_share = True
working_dir = os.path.dirname(os.path.realpath(__file__))
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))


# convert big endian to little endian
def swap32(i):
    return unpack("<I", pack(">I", i))[0]


# split a 32 bit int to 4 seperate bytes
def split_int32_to_bytes(num):
    b1, b2, b3, b4 = (num & 0xFFFFFFFF).to_bytes(4, 'little')
    return [b1, b2, b3, b4]


# applies the encoded key to the masked values
def xor_encoded_numpy(uasset, mask):
    key = frombuffer(b'\xC7\xCE\xB2\xEE', dtype=uint32)[0]
    result = []
    i = 0
    while i < len(mask):
        if mask[i] != 0x00:
            # upon reaching a masked value, read the next 4 bytes (int32)
            uasset_bytes = frombuffer(uasset[i:i+4], dtype=int32)[0]
            encoded_bytes = uint32(uasset_bytes ^ key)
            little_d_bytes = swap32(encoded_bytes)
            result += split_int32_to_bytes(encoded_bytes.item())
            i += 4
        else:
            # append the original value if unmasked
            result.append(uasset[i])
            i += 1
    return result


# converts integers to padded bytes so they can be written to a file easily
def parse_uint32_array(array):
    parsed = []
    for entry in array:
        to_hex = bytes(hex(entry)[2:], 'utf-8')
        entry_len = len(to_hex)
        if (entry_len % 2 == 1):
            to_hex = b'0' + to_hex
        parsed.append(unhexlify(to_hex))
    return parsed


def print_hex(array):
    i = 0
    while i < len(array):
        if i % 16 == 0:
            print()
        if type(array[i]) == bytes:
            print(array[i].hex().upper(), end=' ')
        elif type(array[i]) == int:
            print(hex(array[i]), end=' ')
        i += 1
    print()


# finds all .uasset files in a directory and subdirectory
def get_files_with_ext(directory, extension):
    file_list = []
    if type(extension) != str:
        return file_list
    for root, dirs, files in os.walk(directory):
        for filename in files:
            if extension in filename:
                file_list.append(os.path.join(root, filename))
    return file_list


def is_encoded(header):
    if header[64] == 238:
        return True
    else:
        return False


def encode_files(file_list, decode=False):
    files_not_found = []
    for file in file_list:
        try:
            sourcefile = open(file, 'br+')
        except IOError:
            print(f'{file} does not exist')
            files_not_found.append(file)
            continue
        header = sourcefile.read(170)

        if decode:
            if not is_encoded(header):
                # skip
                sourcefile.close()
                continue
        else:
            if is_encoded(header):
                # skip
                sourcefile.close()
                continue

        encoded = xor_encoded_numpy(header, xor_mask)
        parsed = parse_uint32_array(encoded)
        sourcefile.seek(0)
        for b in parsed:
            sourcefile.write(b)
        sourcefile.close()
    return files_not_found


def clear_meipass():
    try:
        open(sys._MEIPASS + '/is_tof_autopak', 'a').close()

        base_path = (sys._MEIPASS).split("\\")
        base_path.pop(-1)
        temp_path = ""
        for item in base_path:
            temp_path = temp_path + item + "\\"

        mei_folders = [f for f in glob(temp_path + "**/", recursive=False)]
        for item in mei_folders:
            if item.find('_MEI') != -1 and item != sys._MEIPASS + "\\":
                if os.path.exists(item + '/is_tof_autopak'):
                    rmtree(item)
    except AttributeError:
        pass


def load_config():
    if os.path.exists(os.path.join(application_path, 'autopak_conf.env')):
        load_dotenv(os.path.join(application_path, 'autopak_conf.env'))
        disable_share = os.getenv('DISABLE_SHARE') == 'True'
        smol_sig = os.getenv('SMOL_SIG') == 'True'
        game_install_path = os.getenv('GAME_INSTALL_PATH')
        return disable_share, game_install_path, smol_sig
    else:
        print("Config file not found. Select game installation path to create config file.")
        root = Tk()
        root.withdraw()
        game_install_path = filedialog.askdirectory()
        if not game_install_path:
            return

        if game_install_path.endswith("Hotta"):
            game_install_path = game_install_path + '/Content'
        elif game_install_path.endswith("Tower of Fantasy"):
            if game_install_path.count("Tower of Fantasy") == 1:
                game_install_path = game_install_path + '/Tower of Fantasy/Hotta/Content'
            else:
                game_install_path = game_install_path + '/Hotta/Content'

        with open(os.path.join(application_path, 'autopak_conf.env'), 'a') as f:
            f.write(
                f"DISABLE_SHARE=True\nSMOL_SIG=True\nGAME_INSTALL_PATH={game_install_path}")

        return True, game_install_path, True


def main():
    clear_meipass()

    engine_path = os.path.join(
        working_dir, "data/Engine/Binaries/Win64/UnrealPak.exe")
    disable_share_path = os.path.join(working_dir, "data/Share Disable")

    disable_share, game_install_path, smol_sig = load_config()
    if not disable_share or not game_install_path:
        print("An error occurred while loading the config, exiting...")
        input("\nEnter any key to exit...")
        return

    # No argument given
    if len(sys.argv) != 2:
        input("Drag .uasset files or a folder onto this script to run it.\nEnter any key to exit...")
        return

    file_list = []

    # Encode all files in the directory
    if os.path.isdir(sys.argv[1]):
        mod_folder = sys.argv[1]
        copytree(disable_share_path, sys.argv[1], dirs_exist_ok=True)
        file_list = get_files_with_ext(mod_folder, ".uasset")
    # Encode the files given in the argument
    else:
        for i in range(1, len(sys.argv)):
            file_list.append(sys.argv[i])

    # CONFIG
    # Change False below to True to enable decoding
    files_not_found = encode_files(file_list, False)

    if len(files_not_found) > 0:
        for file in files_not_found:
            print(file)
        print("\nThe files above were not encoded since they were not found. Verify the file name or path.")
        print("\nIf run with autopak.bat, the pak file generated will not work")
        input("\nEnter any key to exit...")
        return
    else:
        print("Files encoded successfully\n")

    mods_install_folder = "PatchPaks"
    filelist_parent = "../../../../"

    with open(os.path.join(working_dir, "filelist.txt"), "w") as f:
        f.write(f'"{mod_folder}\*.*" "../../../" -compress')

    if os.path.exists(game_install_path):
        mods_install_folder_path = os.path.join(
            game_install_path, mods_install_folder)
        sig_file_path = os.path.join(
            game_install_path, "Paks/Hotta-WindowsNoEditor.sig")
        if smol_sig:
            sig_file_path = os.path.join(
                working_dir, "data/Hotta-WindowsNoEditor.sig")

        modname = os.path.basename(mod_folder).replace(' ', '')
        pakfile_path = os.path.join(
            mods_install_folder_path, f"Hotta-WindowsNoEditor_{modname}_1_P.pak")
        new_sig_path = os.path.join(
            mods_install_folder_path, f"Hotta-WindowsNoEditor_{modname}_1_P.sig")

        if not os.path.exists(mods_install_folder_path):
            print("Installed mods folder does not exist, creating PatchPaks folder")
            print("To change where mods are created, change the mods_install_folder variable in autopak.py in the Scripts folder.")
            os.makedirs(mods_install_folder_path)

        huh = f"-Create={filelist_parent}filelist.txt"
        print(huh)
        run([engine_path, pakfile_path,
            huh])
        copy(sig_file_path, new_sig_path)
    else:
        print("Invalid game install path. Using default destination. Sig file not created.")
        run([engine_path, f"{mod_folder}.pak",
            f"-Create={filelist_parent}filelist.txt"])

    if disable_share:
        share_disable_path = os.path.join(
            mod_folder, "Hotta/Content/SevenForest/Blueprint/UI/Makeup/")
        os.remove(os.path.join(share_disable_path, "UI_MakeupUpload.uasset"))
        os.remove(os.path.join(share_disable_path, "UI_MakeupUpload.uexp"))

        # remove empty folders
        for root, dirs, files in os.walk(mod_folder, topdown=False):
            for name in dirs:
                dir_path = os.path.join(root, name)
                if not os.listdir(dir_path):  # check if directory is empty
                    os.rmdir(dir_path)

    input("\nEnter any key to exit...")


if __name__ == "__main__":
    main()
