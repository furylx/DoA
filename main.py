import subprocess
import json
from tkinter import messagebox
import ipaddress
import customtkinter
import threading
from concurrent.futures import ThreadPoolExecutor


class PingFrame(customtkinter.CTkFrame):
    def __init__(self, master, device_name, ip_address):
        super().__init__(master)
        self.name = device_name
        self.ip = ip_address


        self.lbl_doa = customtkinter.CTkLabel(self, fg_color='red', text='DEAD', corner_radius=8, height=40, width=50, font=('bold', 16))
        self.lbl_name = customtkinter.CTkLabel(self, text=self.name, fg_color='#525252', corner_radius=8, height=40, width=150, font=('bold', 16))
        self.lbl_ip = customtkinter.CTkLabel(self, text=self.ip, fg_color='#525252', corner_radius=8, height=40, width=150, font=('bold', 16))


        self.lbl_doa.grid(column=0, row=0, padx=5, pady=5)
        self.lbl_name.grid(column=1, row=0, padx=10, pady=10)
        self.lbl_ip.grid(column=2, row=0, padx=10, pady=10)

class PingThread(threading.Thread):
    def __init__(self, executor, device_name, ip_address, frame):
        threading.Thread.__init__(self)
        self.device_name = device_name
        self.ipaddress = ip_address
        self.frame = frame
        self.executor = executor

    def run(self):
        future = self.executor.submit(self.ping)
        future.add_done_callback(self.done_callback)

    def ping(self):
        result = subprocess.run(['ping', '-c', '1', '-t', '5', self.ipaddress], stdout=subprocess.DEVNULL)
        return result.returncode == 0

    def done_callback(self, future):
        if future.result():
            self.frame.lbl_doa.configure(text="ALIVE", fg_color="green")
        else:
            self.frame.lbl_doa.configure(text="DEAD", fg_color="red")


class TopLevel(customtkinter.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.geometry('300x130')
        self.minsize(300, 130)
        self.title('Add new device')
        self.resizable(width=False, height=False)
        self.executor = ThreadPoolExecutor(max_workers=10)

        device_id_lbl = customtkinter.CTkLabel(self, text='New device name')
        device_id_lbl.grid(column=0, row=0, padx=5, pady=5)
        device_ip_lbl = customtkinter.CTkLabel(self, text='New device ip')
        device_ip_lbl.grid(column=0, row=1, padx=5, pady=5)
        self.device_id_entry = customtkinter.CTkEntry(self, placeholder_text='device name')
        self.device_id_entry.grid(column=1, row=0, padx=5, pady=5)
        self.device_ip_entry = customtkinter.CTkEntry(self, placeholder_text='ip address')
        self.device_ip_entry.grid(column=1, row=1, padx=5, pady=5)

        add_btn = customtkinter.CTkButton(self, text='Add', command=self.add_device)
        add_btn.grid(column=1, row=2, padx=5, pady=5)
        cancel_btn = customtkinter.CTkButton(self, text='Cancel', command=self.destroy)
        cancel_btn.grid(column=0, row=2, padx=5, pady=5)

    def add_device(self):
        device_name = self.device_id_entry.get()
        ip_address = self.device_ip_entry.get()

        def is_valid_ip_address(ip_address):
            try:
                ipaddress.IPv4Address(ip_address)
                return True
            except ipaddress.AddressValueError:
                return False

        with open('devices.json', 'r') as f:
            devices = json.load(f)

        if self.device_id_entry.get().strip() == '':
            messagebox.showerror('Error', 'Enter a name.')
        elif device_name in devices:
            messagebox.showerror("Error", "Device name already exists.")
            self.device_id_entry.delete(0,'end')
            self.device_id_entry.configure(placeholder_text='device name')
        elif not is_valid_ip_address(ip_address):
            messagebox.showerror('Error','Please enter a valid IP address')
        elif any(ip_address in device_info for device_info in devices.values()):
            messagebox.showerror("Error", "IP address already being pinged.")
            self.device_ip_entry.delete(0, 'end')
            self.device_ip_entry.configure(placeholder_text='ip address')
        else:
            devices[device_name] = ip_address
            with open('devices.json', 'w') as f:
                json.dump(devices, f, indent=4)

            frame = PingFrame(self.parent, device_name, ip_address)
            self.parent.frames[device_name] = frame
            frame.configure(fg_color='transparent')
            frame.grid(row=len(self.parent.frames) - 1, column=0, sticky='nsew')
            ping_thread = PingThread(self.executor, device_name, ip_address, frame)
            ping_thread.start()
            self.destroy()

class TopLevelRemove(customtkinter.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.geometry('300x130')
        self.minsize(300, 130)
        self.title('Remove')
        self.resizable(width=False, height=False)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        with open('devices.json', 'r') as device_list:
            self.devices = json.load(device_list)
        self.devices_list = [self.device for self.device in self.devices.keys()]
        self.combobox_var = customtkinter.StringVar(value=None)  # set initial value
        self.combobox = customtkinter.CTkComboBox(self, values=self.devices_list, variable=self.combobox_var)
        self.combobox.grid(padx=5, pady=5, sticky='ew')
        self.btn_remove = customtkinter.CTkButton(self, text='Remove', width=50, height=20, command=self.remove_device)
        self.btn_remove.grid(padx=5, pady=20)

    def debug(self):
        print(self.combobox_var.get())

    def remove_device(self):
        # Get the selected device from the combobox
        selected_device = self.combobox_var.get()

        # Remove the device from the devices list and write the updated list to the json file
        with open('devices.json', 'r+') as device_list:
            self.devices = json.load(device_list)
            for device in self.devices:
                if device == selected_device:
                    self.devices.pop(device)
                    break
            device_list.seek(0)
            json.dump(self.devices, device_list, indent=4)
            device_list.truncate()
        self.update_idletasks()
        # Remove the device from the UI
        try:
            if selected_device in self.parent.frames:
                self.parent.frames[selected_device].destroy()
                self.parent.frames.pop(selected_device)
        finally:
            self.update_idletasks()
            self.destroy()

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        #self.geometry("450x400")
        self.title("Dead or Alive")
        self.configure(fg_color='pale violet red')
        #self.minsize(width=380,height=400)
        self.resizable(width=False, height=False)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.executor = ThreadPoolExecutor(max_workers=10)


        with open('devices.json', 'r') as device_list:
            self.devices = json.load(device_list)

        self.frames = {}
        for device_name, ipaddress in self.devices.items():
            frame = PingFrame(self, device_name, ipaddress)
            self.frames[device_name] = frame
            frame.configure(fg_color='transparent')
            frame.grid(column=0, sticky='nsew')
            self.update_idletasks()


        self.btn_start_stop = customtkinter.CTkButton(self, text="Start", height=40, font=('bold', 16), command=self.ping_devices)
        self.btn_start_stop.grid(pady=5, padx=5, sticky='ew', column=1, row=0)

        self.btn_add_device = customtkinter.CTkButton(self, text='Add Device', height=40, font=('bold', 16), command=self.open_toplevel)
        self.btn_add_device.grid(pady=5, padx=5, sticky='ew', column=1, row=1)
        self.btn_remove_device = customtkinter.CTkButton(self, text='Remove Device', height=40, font=('bold', 16), command=self.open_toplevel_remove)
        self.btn_remove_device.grid(pady=5, padx=5, sticky='ew', column=1, row=2)

        self.stop_ping = threading.Event()

        self.top_level_window = None
        self.top_level_window_remove = None


    def open_toplevel(self):
        if self.top_level_window is None or not self.top_level_window.winfo_exists():
            self.top_level_window = TopLevel(self)  # create window if None or destroyed
        else:
            self.top_level_window.focus()
    def open_toplevel_remove(self):
        if self.top_level_window_remove is None or not self.top_level_window_remove.winfo_exists():
            self.top_level_window_remove = TopLevelRemove(self)
        else:
            self.top_level_window_remove.focus()

    def ping_devices(self):
        if self.btn_start_stop.cget('text') == 'Start':
            self.btn_start_stop.configure(text='Stop')
            self.btn_add_device.configure(state='disabled')
            self.btn_remove_device.configure(state='disabled')
            self.stop_ping.clear()
            self.configure(bg='grey')
            self.ping_thread = threading.Thread(target=self.ping_loop)
            self.ping_thread.start()
        else:
            self.btn_start_stop.configure(text='Start')
            self.btn_add_device.configure(state='normal')
            self.btn_remove_device.configure(state='normal')
            self.configure(bg='pale violet red')
            self.stop_ping_loop()

    def ping_loop(self):
        while not self.stop_ping.is_set():
            for device_name, ipaddress in self.devices.items():
                t = PingThread(self.executor, device_name, ipaddress, self.frames[device_name])
                t.start()
            self.stop_ping.wait(5)

    def stop_ping_loop(self):
        self.stop_ping.set()
        self.ping_thread.join()


if __name__ == '__main__':
    app = App()
    app.mainloop()
