#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import re
import json

# Graceful Import of Cisco Cobra ACI SDK
COBRA_AVAILABLE = False
try:
    import cobra.mit.access
    import cobra.mit.request
    import cobra.mit.session
    import cobra.model.bgp
    import cobra.model.ospf
    import cobra.model.eigrp
    import cobra.model.fv
    import cobra.model.l3ext
    import cobra.model.pol
    import cobra.model.top
    
    # Import model implementations to help PyInstaller analyze dynamic dependencies
    import cobra.modelimpl.bgp
    import cobra.modelimpl.ospf
    import cobra.modelimpl.eigrp
    import cobra.modelimpl.fv
    import cobra.modelimpl.l3ext
    import cobra.modelimpl.pol
    import cobra.modelimpl.top
    
    from cobra.internal.codec.xmlcodec import toXMLStr
    COBRA_AVAILABLE = True
except ImportError:
    pass

class BGP_L3OutApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.session_md = None
        self.title("Cisco ACI L3Out Creator (BGP/OSPF/EIGRP/Static)")
        self.geometry("950x800")
        self.minsize(900, 650)

        # Style Configuration
        self.style = ttk.Style(self)
        self.style.theme_use("winnative")
        
        # Color definitions
        self.bg_color = "#f3f3f3"
        self.configure(background=self.bg_color)

        # ----------------- Menu Bar & Help/About -----------------
        self.menu_bar = tk.Menu(self)
        self.config(menu=self.menu_bar)

        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.file_menu.add_command(label="Exit", command=self.confirm_exit)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)

        self.help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.help_menu.add_command(label="About", command=self.show_about)
        self.menu_bar.add_cascade(label="Help", menu=self.help_menu)

        # Intercept window close event to exit gracefully
        self.protocol("WM_DELETE_WINDOW", self.confirm_exit)

        # ----------------- Navy Blue Glossy Header -----------------
        self.header_frame = tk.Frame(self, bg="#1A365D", height=65)
        self.header_frame.pack(fill=tk.X)
        self.header_frame.pack_propagate(False)

        # Glossy Accent Bar (Highlight line)
        self.accent_bar = tk.Frame(self, bg="#4A90E2", height=3)
        self.accent_bar.pack(fill=tk.X)

        title_label = tk.Label(
            self.header_frame, 
            text="CISCO ACI L3OUT CREATOR", 
            font=("Calibri", 16, "bold"), 
            fg="white", 
            bg="#1A365D"
        )
        title_label.pack(anchor="w", padx=15, pady=(8, 0))

        subtitle_label = tk.Label(
            self.header_frame, 
            text="Multi-Protocol Automation Engine", 
            font=("Calibri", 9, "italic"), 
            fg="#A5C2F3", 
            bg="#1A365D"
        )
        subtitle_label.pack(anchor="w", padx=15, pady=(0, 5))
        
        # Main container
        main_container = ttk.Frame(self, padding="10")
        main_container.pack(fill=tk.BOTH, expand=True)

        # Warning banner if Cobra SDK is not installed
        if not COBRA_AVAILABLE:
            banner = tk.Frame(main_container, bg="#fff3cd", bd=1, relief=tk.SOLID)
            banner.pack(fill=tk.X, pady=(0, 10))
            banner_label = tk.Label(
                banner, 
                text="⚠️ Cisco Cobra SDK not detected in Python 3 environment. Application running in Mock/Simulation Mode.",
                bg="#fff3cd", 
                fg="#856404",
                font=("Arial", 10, "bold")
            )
            banner_label.pack(anchor="w", padx=5, pady=5)

        # ----------------- Connection Frame -----------------
        conn_frame = ttk.LabelFrame(main_container, text="APIC Connection Settings", padding="10")
        conn_frame.pack(fill=tk.X, pady=(0, 10))

        # Grid configuration for Connection Frame
        conn_frame.columnconfigure(1, weight=1)
        conn_frame.columnconfigure(3, weight=1)
        conn_frame.columnconfigure(5, weight=1)

        ttk.Label(conn_frame, text="APIC URL/IP:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.apic_url_var = tk.StringVar(value="https://1.1.1.1")
        self.apic_url_entry = ttk.Entry(conn_frame, textvariable=self.apic_url_var)
        self.apic_url_entry.grid(row=0, column=1, sticky=tk.EW, padx=(0, 15))

        ttk.Label(conn_frame, text="Username:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.username_var = tk.StringVar(value="admin")
        self.username_entry = ttk.Entry(conn_frame, textvariable=self.username_var)
        self.username_entry.grid(row=0, column=3, sticky=tk.EW, padx=(0, 15))

        ttk.Label(conn_frame, text="Password:").grid(row=0, column=4, sticky=tk.W, padx=(0, 5))
        self.password_var = tk.StringVar(value="password")
        self.password_entry = ttk.Entry(conn_frame, textvariable=self.password_var, show="*")
        self.password_entry.grid(row=0, column=5, sticky=tk.EW, padx=(0, 15))

        self.btn_fetch = ttk.Button(conn_frame, text="Fetch APIC Data", command=self.action_fetch_apic)
        self.btn_fetch.grid(row=0, column=6, sticky=tk.E)

        self.btn_logout = ttk.Button(conn_frame, text="Logout APIC", command=self.action_logout_apic)
        self.btn_logout.grid(row=1, column=6, sticky=tk.E, pady=(5, 0))

        # ----------------- Control Buttons Frame (Packed at bottom to ensure visibility) -----------------
        btn_frame = ttk.Frame(main_container)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        self.btn_push = ttk.Button(btn_frame, text="Push Configuration to APIC", command=self.action_push)
        self.btn_push.pack(side=tk.RIGHT)

        # ----------------- Tabbed Settings Frame (Packed to fill remaining space) -----------------
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(0, 10))

        # Tab 1: General/Hierarchy Settings
        self.tab_general = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.tab_general, text="1. General Settings")
        self.setup_general_tab()

        # Tab 2: Leaf Nodes Configuration
        self.tab_nodes = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.tab_nodes, text="2. Leaf Nodes")
        self.setup_nodes_tab()

        # Tab 3: Interface Path Attachments
        self.tab_interfaces = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.tab_interfaces, text="3. Interfaces")
        self.setup_interfaces_tab()

        # Tab 4: Action Console
        self.tab_console = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.tab_console, text="4. Action Console")
        self.setup_console_tab()

    def log(self, message):
        """Append a message to the console text box."""
        self.console.insert(tk.END, message + "\n")
        self.console.see(tk.END)

    def show_about(self):
        """Display dialog with version, rights and author details."""
        about_text = (
            "Cisco ACI L3Out Creator\n"
            "Version 2.0.0\n\n"
            "Author: Shafie Afridi\n"
            "Rights: © 2026 Shafie Afridi. All rights reserved.\n\n"
            "A professional automated configuration engine for Cisco ACI fabrics using the Cobra SDK."
        )
        messagebox.showinfo("About Application", about_text, parent=self)

    def confirm_exit(self):
        """Show confirmation dialog before exiting the app."""
        if messagebox.askyesno("Exit Application", "Are you sure you want to exit?"):
            self.destroy()

    def setup_general_tab(self):
        self.tab_general.columnconfigure(1, weight=1)

        # Tenant Selection
        ttk.Label(self.tab_general, text="Tenant Name:").grid(row=0, column=0, sticky=tk.W, pady=6, padx=(0, 10))
        self.tenant_var = tk.StringVar(value="NON-PROD_TEST")
        self.tenant_combo = ttk.Combobox(self.tab_general, textvariable=self.tenant_var)
        self.tenant_combo.grid(row=0, column=1, sticky=tk.EW, pady=6)
        self.tenant_combo.bind("<<ComboboxSelected>>", self.on_tenant_change)

        # VRF (Ctx) Selection
        ttk.Label(self.tab_general, text="VRF Name (Ctx):").grid(row=1, column=0, sticky=tk.W, pady=6, padx=(0, 10))
        self.vrf_var = tk.StringVar(value="NON-PROD.VRF")
        self.vrf_combo = ttk.Combobox(self.tab_general, textvariable=self.vrf_var)
        self.vrf_combo.grid(row=1, column=1, sticky=tk.EW, pady=6)

        # L3Out Name Selection
        ttk.Label(self.tab_general, text="L3Out Name:").grid(row=2, column=0, sticky=tk.W, pady=6, padx=(0, 10))
        self.l3out_var = tk.StringVar(value="NON-PROD.L3OUT")
        self.l3out_combo = ttk.Combobox(self.tab_general, textvariable=self.l3out_var)
        self.l3out_combo.grid(row=2, column=1, sticky=tk.EW, pady=6)

        # L3 Domain Selection
        ttk.Label(self.tab_general, text="L3 Domain:").grid(row=3, column=0, sticky=tk.W, pady=6, padx=(0, 10))
        self.l3dom_var = tk.StringVar(value="EXTERNAL-L3")
        self.l3dom_combo = ttk.Combobox(self.tab_general, textvariable=self.l3dom_var)
        self.l3dom_combo.grid(row=3, column=1, sticky=tk.EW, pady=6)

        # Node Profile Name
        ttk.Label(self.tab_general, text="Node Profile Name:").grid(row=4, column=0, sticky=tk.W, pady=6, padx=(0, 10))
        self.node_prof_var = tk.StringVar(value="BORDER-NODES")
        self.node_prof_entry = ttk.Entry(self.tab_general, textvariable=self.node_prof_var)
        self.node_prof_entry.grid(row=4, column=1, sticky=tk.EW, pady=6)

        # Interface Profile Name
        ttk.Label(self.tab_general, text="Interface Profile Name:").grid(row=5, column=0, sticky=tk.W, pady=6, padx=(0, 10))
        self.if_prof_var = tk.StringVar(value="CORE-FACING")
        self.if_prof_entry = ttk.Entry(self.tab_general, textvariable=self.if_prof_var)
        self.if_prof_entry.grid(row=5, column=1, sticky=tk.EW, pady=6)

        # Protocol selection combobox (includes Static routing option)
        ttk.Label(self.tab_general, text="Routing Protocol:").grid(row=6, column=0, sticky=tk.W, pady=6, padx=(0, 10))
        self.protocol_var = tk.StringVar(value="BGP")
        self.protocol_combo = ttk.Combobox(self.tab_general, textvariable=self.protocol_var, values=["BGP", "OSPF", "EIGRP", "Static"], state="readonly")
        self.protocol_combo.grid(row=6, column=1, sticky=tk.EW, pady=6)
        self.protocol_combo.bind("<<ComboboxSelected>>", self.on_protocol_change)

        # Protocol parameter dynamic entry
        self.lbl_proto_param = ttk.Label(self.tab_general, text="BGP AS Number:")
        self.lbl_proto_param.grid(row=7, column=0, sticky=tk.W, pady=6, padx=(0, 10))
        self.proto_param_var = tk.StringVar(value="(Inherited from Route Reflector)")
        self.proto_param_entry = ttk.Entry(self.tab_general, textvariable=self.proto_param_var, state="disabled")
        self.proto_param_entry.grid(row=7, column=1, sticky=tk.EW, pady=6)

    def on_protocol_change(self, event=None):
        proto = self.protocol_var.get()
        if proto == "BGP":
            self.lbl_proto_param.config(text="BGP AS Number:")
            self.proto_param_var.set("(Inherited from Route Reflector)")
            self.proto_param_entry.config(state="disabled")
            
            # Enable BGP Peer inputs on Interfaces tab
            self.entry_if_peer_ip.config(state="normal")
            self.entry_if_peer_asn.config(state="normal")
            self.entry_if_peer_ttl.config(state="normal")
        elif proto == "OSPF":
            self.lbl_proto_param.config(text="OSPF Area ID:")
            self.proto_param_var.set("0.0.0.104")
            self.proto_param_entry.config(state="normal")
            
            # Disable BGP Peer inputs on Interfaces tab
            self.entry_if_peer_ip.config(state="disabled")
            self.entry_if_peer_asn.config(state="disabled")
            self.entry_if_peer_ttl.config(state="disabled")
        elif proto == "EIGRP":
            self.lbl_proto_param.config(text="EIGRP AS Number:")
            self.proto_param_var.set("100")
            self.proto_param_entry.config(state="normal")
            
            # Disable BGP Peer inputs on Interfaces tab
            self.entry_if_peer_ip.config(state="disabled")
            self.entry_if_peer_asn.config(state="disabled")
            self.entry_if_peer_ttl.config(state="disabled")
        elif proto == "Static":
            self.lbl_proto_param.config(text="Routing Profile:")
            self.proto_param_var.set("-")
            self.proto_param_entry.config(state="disabled")
            
            # Disable BGP Peer inputs on Interfaces tab
            self.entry_if_peer_ip.config(state="disabled")
            self.entry_if_peer_asn.config(state="disabled")
            self.entry_if_peer_ttl.config(state="disabled")

    def on_if_type_change(self, event=None):
        if_type = self.combo_if_type.get()
        if if_type == "Routed":
            self.entry_if_vlan.delete(0, tk.END)
            self.entry_if_vlan.insert(0, "-")
            self.entry_if_vlan.config(state="disabled")
        else:
            if self.entry_if_vlan.get() == "-":
                self.entry_if_vlan.delete(0, tk.END)
            self.entry_if_vlan.config(state="normal")

    def action_fetch_apic(self):
        url = self.apic_url_var.get().strip()
        user = self.username_var.get().strip()
        pwd = self.password_var.get().strip()
        
        if not url or not user or not pwd:
            messagebox.showerror("Connection Error", "Please complete all APIC Connection Settings first.")
            return

        self.notebook.select(self.tab_console)  # Switch tab to console
        self.log("Starting background query to fetch APIC objects...")
        self.btn_fetch.config(state="disabled")
        
        thread = threading.Thread(target=self.fetch_process, args=(url, user, pwd))
        thread.daemon = True
        thread.start()

    def fetch_process(self, url, user, pwd):
        if not COBRA_AVAILABLE:
            # Load simulated APIC data for mock mode
            self.log("[SIMULATION] Connecting to APIC at " + url + " ...")
            self.log("[SIMULATION] Querying fvTenant, fvCtx, l3extDomP, l3extOut...")
            
            # Setup simulated database
            sim_data = {
                "tenants": ["NON-PROD_TEST", "WDM", "Production_Tenant"],
                "vrfs": {
                    "NON-PROD_TEST": ["NON-PROD.VRF", "DEV.VRF"],
                    "WDM": ["CTX", "WDM_VRF"],
                    "Production_Tenant": ["Prod_VRF", "DMZ_VRF"]
                },
                "l3outs": {
                    "NON-PROD_TEST": ["NON-PROD.L3OUT", "DEV-BGP.L3OUT"],
                    "WDM": ["CTX-CORE", "WDM-OSPF.L3OUT"],
                    "Production_Tenant": ["Prod-BGP.L3OUT"]
                },
                "l3doms": ["EXTERNAL-L3", "L3DOM-CORE", "PHYS-DOM"]
            }
            
            # Update GUI variables on main thread
            self.after(0, lambda: self.update_apic_combos(sim_data))
            self.log("[SIMULATION] Mock data populated successfully.")
            self.after(0, lambda: messagebox.showinfo("Fetch Complete", "Simulation Mode: Mock ACI objects populated!"))
            return

        self.log(f"Connecting to APIC: {url} ...")
        try:
            ls = cobra.mit.session.LoginSession(url, user, pwd)
            md = cobra.mit.access.MoDirectory(ls)
            md.login()
            self.session_md = md  # Store session for logging out later
            self.log("Authenticated successfully. Fetching classes...")

            # Query ACI MIT
            self.log("Querying Tenants (fvTenant)...")
            tenants = md.lookupByClass('fvTenant')
            self.log(f"Found {len(tenants)} Tenants.")

            self.log("Querying VRFs (fvCtx)...")
            vrfs = md.lookupByClass('fvCtx')
            self.log(f"Found {len(vrfs)} VRFs.")

            self.log("Querying L3 Domains (l3extDomP)...")
            l3doms = md.lookupByClass('l3extDomP')
            self.log(f"Found {len(l3doms)} L3 Domains.")

            self.log("Querying L3Outs (l3extOut)...")
            l3outs = md.lookupByClass('l3extOut')
            self.log(f"Found {len(l3outs)} L3Outs.")

            # Process database
            apic_db = {
                "tenants": [],
                "vrfs": {},
                "l3outs": {},
                "l3doms": []
            }

            for t in tenants:
                t_name = str(t.name)
                apic_db["tenants"].append(t_name)
                apic_db["vrfs"][t_name] = []
                apic_db["l3outs"][t_name] = []

            for v in vrfs:
                # Find parent tenant name
                parent_dn = str(v.dn)
                match = re.match(r"^uni/tn-([^/]+)/ctx-", parent_dn)
                if match:
                    t_name = match.group(1)
                    if t_name in apic_db["vrfs"]:
                        apic_db["vrfs"][t_name].append(str(v.name))

            for l3d in l3doms:
                apic_db["l3doms"].append(str(l3d.name))

            for out in l3outs:
                parent_dn = str(out.dn)
                match = re.match(r"^uni/tn-([^/]+)/out-", parent_dn)
                if match:
                    t_name = match.group(1)
                    if t_name in apic_db["l3outs"]:
                        apic_db["l3outs"][t_name].append(str(out.name))

            # Sort lists
            apic_db["tenants"].sort()
            apic_db["l3doms"].sort()
            for t_name in apic_db["vrfs"]:
                apic_db["vrfs"][t_name].sort()
                apic_db["l3outs"][t_name].sort()

            # Update GUI variables on main thread
            self.after(0, lambda: self.update_apic_combos(apic_db))
            self.log("APIC database loaded and populated successfully.")
            self.after(0, lambda: messagebox.showinfo("Fetch Complete", "ACI Objects fetched and populated successfully!"))

        except Exception as e:
            self.log(f"ERROR: Failed to fetch APIC objects: {str(e)}")
            self.after(0, lambda: messagebox.showerror("Fetch Error", f"Failed to fetch ACI objects:\n{str(e)}"))
        finally:
            self.after(0, lambda: self.btn_fetch.config(state="normal"))

    def action_logout_apic(self):
        """Start background logout process."""
        self.notebook.select(self.tab_console)  # Switch tab to console
        self.log("Initiating logout from APIC...")
        self.btn_logout.config(state="disabled")
        
        thread = threading.Thread(target=self.logout_process)
        thread.daemon = True
        thread.start()

    def logout_process(self):
        # 1. Handle APIC SDK Logout if session exists
        if COBRA_AVAILABLE and getattr(self, "session_md", None) is not None:
            try:
                self.log("Sending logout request to APIC...")
                self.session_md.logout()
                self.log("APIC session terminated successfully.")
            except Exception as e:
                self.log(f"Notice: APIC session logout error: {str(e)}")
            finally:
                self.session_md = None
        else:
            self.log("[SIMULATION] APIC session terminated successfully.")

        # 2. Clear fetched data and update UI variables on main thread
        def reset_ui():
            self.tenant_combo.config(values=[])
            self.vrf_combo.config(values=[])
            self.l3out_combo.config(values=[])
            self.l3dom_combo.config(values=[])
            
            self.tenant_var.set("")
            self.vrf_var.set("")
            self.l3out_var.set("")
            self.l3dom_var.set("")
            
            if hasattr(self, "apic_db"):
                delattr(self, "apic_db")
                
            self.btn_logout.config(state="normal")
            self.log("Local APIC cache cleared. UI reset completed.")
            messagebox.showinfo("Logout Complete", "Successfully logged out from APIC and cleared local cache.")

        self.after(0, reset_ui)

    def update_apic_combos(self, db):
        self.apic_db = db
        
        # Populate Tenant Combobox
        self.tenant_combo.config(values=db["tenants"])
        if db["tenants"]:
            default_t = "NON-PROD_TEST"
            if default_t in db["tenants"]:
                self.tenant_var.set(default_t)
            else:
                self.tenant_var.set(db["tenants"][0])
            self.on_tenant_change()

        # Populate L3Domain Combobox
        self.l3dom_combo.config(values=db["l3doms"])
        if db["l3doms"]:
            default_d = "EXTERNAL-L3"
            if default_d in db["l3doms"]:
                self.l3dom_var.set(default_d)
            else:
                self.l3dom_var.set(db["l3doms"][0])
                
        self.btn_fetch.config(state="normal")

    def on_tenant_change(self, event=None):
        t_name = self.tenant_var.get().strip()
        if hasattr(self, "apic_db") and t_name in self.apic_db["vrfs"]:
            # Update VRF values
            vrf_list = self.apic_db["vrfs"][t_name]
            self.vrf_combo.config(values=vrf_list)
            if vrf_list:
                self.vrf_var.set(vrf_list[0])
            else:
                self.vrf_var.set("")

            # Update L3Out values
            l3out_list = self.apic_db["l3outs"][t_name]
            self.l3out_combo.config(values=l3out_list)
            if l3out_list:
                self.l3out_var.set(l3out_list[0])
            else:
                self.l3out_var.set("")

    def setup_nodes_tab(self):
        self.tab_nodes.columnconfigure(0, weight=1)
        self.tab_nodes.rowconfigure(0, weight=1)

        # Treeview to display nodes
        columns = ("pod_id", "node_id", "router_id")
        self.node_tree = ttk.Treeview(self.tab_nodes, columns=columns, show="headings", height=5)
        self.node_tree.heading("pod_id", text="Pod ID")
        self.node_tree.heading("node_id", text="Node ID")
        self.node_tree.heading("router_id", text="Router ID (Loopback IP)")
        
        self.node_tree.column("pod_id", width=100, anchor=tk.CENTER)
        self.node_tree.column("node_id", width=150, anchor=tk.CENTER)
        self.node_tree.column("router_id", width=250, anchor=tk.CENTER)
        
        self.node_tree.grid(row=0, column=0, columnspan=2, sticky=tk.NSEW, pady=(0, 5))

        # Scrollbar for treeview
        sb = ttk.Scrollbar(self.tab_nodes, orient=tk.VERTICAL, command=self.node_tree.yview)
        self.node_tree.configure(yscrollcommand=sb.set)
        sb.grid(row=0, column=2, sticky=tk.NS, pady=(0, 5))

        # Default nodes
        self.node_tree.insert("", tk.END, values=("1", "1011", "10.1.1.150"))
        self.node_tree.insert("", tk.END, values=("1", "1012", "10.1.1.151"))

        # Add/Remove Controls Frame
        ctrl_frame = ttk.Frame(self.tab_nodes)
        ctrl_frame.grid(row=1, column=0, columnspan=3, sticky=tk.EW, pady=5)

        ttk.Label(ctrl_frame, text="Pod:").grid(row=0, column=0, padx=2)
        self.entry_node_pod = ttk.Entry(ctrl_frame, width=5)
        self.entry_node_pod.insert(0, "1")
        self.entry_node_pod.grid(row=0, column=1, padx=5)

        ttk.Label(ctrl_frame, text="Node ID:").grid(row=0, column=2, padx=2)
        self.entry_node_id = ttk.Entry(ctrl_frame, width=10)
        self.entry_node_id.grid(row=0, column=3, padx=5)

        ttk.Label(ctrl_frame, text="Router ID:").grid(row=0, column=4, padx=2)
        self.entry_node_rtr = ttk.Entry(ctrl_frame, width=15)
        self.entry_node_rtr.grid(row=0, column=5, padx=5)

        btn_add = ttk.Button(ctrl_frame, text="Add Node", command=self.add_node)
        btn_add.grid(row=0, column=6, padx=5)

        btn_remove = ttk.Button(ctrl_frame, text="Remove Selected", command=self.remove_node)
        btn_remove.grid(row=0, column=7, padx=5)

    def setup_interfaces_tab(self):
        self.tab_interfaces.columnconfigure(0, weight=1)
        self.tab_interfaces.rowconfigure(0, weight=1)

        # Treeview to display interface path attachments (expanded with BGP Peer details)
        columns = ("pod_id", "node_id", "port", "ip_addr", "if_type", "vlan", "mac", "peer_ip", "peer_asn", "peer_ttl")
        self.if_tree = ttk.Treeview(self.tab_interfaces, columns=columns, show="headings", height=5)
        self.if_tree.heading("pod_id", text="Pod")
        self.if_tree.heading("node_id", text="Node ID")
        self.if_tree.heading("port", text="Port")
        self.if_tree.heading("ip_addr", text="IP Address/Mask")
        self.if_tree.heading("if_type", text="Type")
        self.if_tree.heading("vlan", text="VLAN")
        self.if_tree.heading("mac", text="MAC Address")
        self.if_tree.heading("peer_ip", text="BGP Peer IP")
        self.if_tree.heading("peer_asn", text="Remote AS")
        self.if_tree.heading("peer_ttl", text="TTL")

        self.if_tree.column("pod_id", width=40, anchor=tk.CENTER)
        self.if_tree.column("node_id", width=60, anchor=tk.CENTER)
        self.if_tree.column("port", width=80, anchor=tk.CENTER)
        self.if_tree.column("ip_addr", width=120, anchor=tk.CENTER)
        self.if_tree.column("if_type", width=95, anchor=tk.CENTER)
        self.if_tree.column("vlan", width=50, anchor=tk.CENTER)
        self.if_tree.column("mac", width=130, anchor=tk.CENTER)
        self.if_tree.column("peer_ip", width=100, anchor=tk.CENTER)
        self.if_tree.column("peer_asn", width=70, anchor=tk.CENTER)
        self.if_tree.column("peer_ttl", width=40, anchor=tk.CENTER)

        self.if_tree.grid(row=0, column=0, columnspan=2, sticky=tk.NSEW, pady=(0, 5))

        sb = ttk.Scrollbar(self.tab_interfaces, orient=tk.VERTICAL, command=self.if_tree.yview)
        self.if_tree.configure(yscrollcommand=sb.set)
        sb.grid(row=0, column=2, sticky=tk.NS, pady=(0, 5))

        # Default paths
        default_ifs = [
            ("1", "1011", "eth1/1", "10.1.3.198/30", "Sub-Interface", "103", "00:22:BD:F8:19:FF", "10.1.3.197", "65001", "1"),
            ("1", "1012", "eth1/1", "10.1.3.202/30", "Sub-Interface", "103", "00:22:BD:F8:19:FF", "10.1.3.201", "65001", "1"),
            ("1", "1011", "eth1/2", "10.1.4.1/30", "Routed", "-", "00:22:BD:F8:19:FF", "10.1.4.2", "65001", "1"),
            ("1", "1012", "eth1/2", "10.1.5.1/24", "SVI", "104", "00:22:BD:F8:19:FF", "10.1.5.2", "65001", "1")
        ]
        for item in default_ifs:
            self.if_tree.insert("", tk.END, values=item)

        # Control fields frame
        ctrl_frame = ttk.Frame(self.tab_interfaces)
        ctrl_frame.grid(row=1, column=0, columnspan=3, sticky=tk.EW, pady=5)

        # Row 0: Basic interface details
        ttk.Label(ctrl_frame, text="Type:").grid(row=0, column=0, padx=2, pady=2, sticky=tk.E)
        self.combo_if_type = ttk.Combobox(ctrl_frame, values=["Sub-Interface", "Routed", "SVI"], state="readonly", width=14)
        self.combo_if_type.set("Sub-Interface")
        self.combo_if_type.grid(row=0, column=1, padx=5, pady=2)
        self.combo_if_type.bind("<<ComboboxSelected>>", self.on_if_type_change)

        ttk.Label(ctrl_frame, text="Pod:").grid(row=0, column=2, padx=2, pady=2, sticky=tk.E)
        self.entry_if_pod = ttk.Entry(ctrl_frame, width=5)
        self.entry_if_pod.insert(0, "1")
        self.entry_if_pod.grid(row=0, column=3, padx=5, pady=2)

        ttk.Label(ctrl_frame, text="Node ID:").grid(row=0, column=4, padx=2, pady=2, sticky=tk.E)
        self.entry_if_node = ttk.Entry(ctrl_frame, width=8)
        self.entry_if_node.grid(row=0, column=5, padx=5, pady=2)

        ttk.Label(ctrl_frame, text="Port:").grid(row=0, column=6, padx=2, pady=2, sticky=tk.E)
        self.entry_if_port = ttk.Entry(ctrl_frame, width=10)
        self.entry_if_port.insert(0, "eth1/1")
        self.entry_if_port.grid(row=0, column=7, padx=5, pady=2)

        ttk.Label(ctrl_frame, text="IP/Mask:").grid(row=0, column=8, padx=2, pady=2, sticky=tk.E)
        self.entry_if_ip = ttk.Entry(ctrl_frame, width=16)
        self.entry_if_ip.grid(row=0, column=9, padx=5, pady=2)

        ttk.Label(ctrl_frame, text="VLAN:").grid(row=0, column=10, padx=2, pady=2, sticky=tk.E)
        self.entry_if_vlan = ttk.Entry(ctrl_frame, width=6)
        self.entry_if_vlan.grid(row=0, column=11, padx=5, pady=2)

        ttk.Label(ctrl_frame, text="MAC:").grid(row=0, column=12, padx=2, pady=2, sticky=tk.E)
        self.entry_if_mac = ttk.Entry(ctrl_frame, width=17)
        self.entry_if_mac.insert(0, "00:22:BD:F8:19:FF")
        self.entry_if_mac.grid(row=0, column=13, padx=5, pady=2)

        # Row 1: BGP Peer details
        ttk.Label(ctrl_frame, text="Peer IP:").grid(row=1, column=0, padx=2, pady=2, sticky=tk.E)
        self.entry_if_peer_ip = ttk.Entry(ctrl_frame, width=15)
        self.entry_if_peer_ip.grid(row=1, column=1, padx=5, pady=2, sticky=tk.W)

        ttk.Label(ctrl_frame, text="Remote ASN:").grid(row=1, column=2, padx=2, pady=2, sticky=tk.E)
        self.entry_if_peer_asn = ttk.Entry(ctrl_frame, width=10)
        self.entry_if_peer_asn.insert(0, "65001")
        self.entry_if_peer_asn.grid(row=1, column=3, padx=5, pady=2)

        ttk.Label(ctrl_frame, text="Peer TTL:").grid(row=1, column=4, padx=2, pady=2, sticky=tk.E)
        self.entry_if_peer_ttl = ttk.Entry(ctrl_frame, width=8)
        self.entry_if_peer_ttl.insert(0, "1")
        self.entry_if_peer_ttl.grid(row=1, column=5, padx=5, pady=2)

        # Buttons on Row 1 (spanning the rest of columns)
        btn_frame = ttk.Frame(ctrl_frame)
        btn_frame.grid(row=1, column=6, columnspan=8, sticky=tk.E, padx=5, pady=2)
        
        btn_add = ttk.Button(btn_frame, text="Add Interface", command=self.add_interface)
        btn_add.pack(side=tk.LEFT, padx=5)

        btn_remove = ttk.Button(btn_frame, text="Remove Selected", command=self.remove_interface)
        btn_remove.pack(side=tk.LEFT, padx=5)

    def setup_console_tab(self):
        self.tab_console.columnconfigure(0, weight=1)
        self.tab_console.rowconfigure(0, weight=1)
        self.tab_console.rowconfigure(1, weight=0)

        log_frame = ttk.LabelFrame(self.tab_console, text="Action Console / Log Output", padding="5")
        log_frame.grid(row=0, column=0, sticky=tk.NSEW, pady=(0, 5))

        self.console = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, font=("Consolas", 10))
        self.console.pack(fill=tk.BOTH, expand=True)
        self.log("L3Out Creator utility initialized.")
        if not COBRA_AVAILABLE:
            self.log("Notice: Simulation Mode is active. Previews and commits generate simulated outputs.")

        # Console Button Frame for Validate and Preview buttons
        console_btn_frame = ttk.Frame(self.tab_console)
        console_btn_frame.grid(row=1, column=0, sticky=tk.EW)

        self.btn_validate = ttk.Button(console_btn_frame, text="Validate Inputs", command=self.action_validate)
        self.btn_validate.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_preview = ttk.Button(console_btn_frame, text="Preview JSON Output", command=self.action_preview)
        self.btn_preview.pack(side=tk.LEFT)

    # ----------------- Actions & Logic -----------------

    def add_node(self):
        pod = self.entry_node_pod.get().strip()
        node = self.entry_node_id.get().strip()
        rtr = self.entry_node_rtr.get().strip()

        if not pod.isdigit() or not node.isdigit() or not rtr:
            messagebox.showerror("Invalid Input", "Pod and Node ID must be numeric, and Router ID IP must not be blank.")
            return

        self.node_tree.insert("", tk.END, values=(pod, node, rtr))
        self.entry_node_id.delete(0, tk.END)
        self.entry_node_rtr.delete(0, tk.END)

    def remove_node(self):
        selected = self.node_tree.selection()
        if not selected:
            messagebox.showwarning("Select Node", "Please select a node row in the table to remove.")
            return
        for s in selected:
            self.node_tree.delete(s)

    def add_interface(self):
        pod = self.entry_if_pod.get().strip()
        node = self.entry_if_node.get().strip()
        port = self.entry_if_port.get().strip()
        ip = self.entry_if_ip.get().strip()
        if_type = self.combo_if_type.get()
        vlan = self.entry_if_vlan.get().strip()
        mac = self.entry_if_mac.get().strip()

        proto = self.protocol_var.get()
        if proto == "BGP":
            peer_ip = self.entry_if_peer_ip.get().strip()
            peer_asn = self.entry_if_peer_asn.get().strip()
            peer_ttl = self.entry_if_peer_ttl.get().strip()
            if not peer_ip or not peer_asn or not peer_ttl:
                messagebox.showerror("Invalid Input", "BGP Peer IP, Remote AS, and TTL are required for BGP routing.")
                return
        else:
            peer_ip = "-"
            peer_asn = "-"
            peer_ttl = "-"

        if if_type == "Routed":
            vlan = "-"

        if not pod.isdigit() or not node.isdigit() or not port or not ip or not vlan or not mac:
            messagebox.showerror("Invalid Input", "Please fill in all standard interface path fields. Pod and Node ID must be numeric.")
            return

        self.if_tree.insert("", tk.END, values=(pod, node, port, ip, if_type, vlan, mac, peer_ip, peer_asn, peer_ttl))
        self.entry_if_node.delete(0, tk.END)
        self.entry_if_ip.delete(0, tk.END)
        
        # Reset VLAN field to default state depending on selected type
        self.entry_if_vlan.config(state="normal")
        self.entry_if_vlan.delete(0, tk.END)
        if if_type == "Routed":
            self.entry_if_vlan.insert(0, "-")
            self.entry_if_vlan.config(state="disabled")

        if proto == "BGP":
            self.entry_if_peer_ip.delete(0, tk.END)

    def remove_interface(self):
        selected = self.if_tree.selection()
        if not selected:
            messagebox.showwarning("Select Interface", "Please select an interface row in the table to remove.")
            return
        for s in selected:
            self.if_tree.delete(s)

    def get_and_validate_inputs(self):
        """Validates all screen inputs. Returns a dict on success, None on failure."""
        data = {
            "apic_url": self.apic_url_var.get().strip(),
            "username": self.username_var.get().strip(),
            "password": self.password_var.get().strip(),
            "tenant": self.tenant_var.get().strip(),
            "vrf": self.vrf_var.get().strip(),
            "l3out": self.l3out_var.get().strip(),
            "l3dom": self.l3dom_var.get().strip(),
            "node_profile": self.node_prof_var.get().strip(),
            "interface_profile": self.if_prof_var.get().strip(),
            "protocol": self.protocol_var.get(),
            "proto_param": self.proto_param_var.get().strip(),
            "nodes": [],
            "interfaces": []
        }

        # Check connection settings
        if not data["apic_url"] or not data["username"] or not data["password"]:
            messagebox.showerror("Validation Error", "All APIC Connection settings must be completed.")
            return None

        # Check ACI hierarchy settings
        if not data["tenant"] or not data["vrf"] or not data["l3out"] or not data["l3dom"] or not data["node_profile"] or not data["interface_profile"] or not data["proto_param"]:
            messagebox.showerror("Validation Error", "All general settings must be completed.")
            return None

        # Protocol parameter checks
        ip_regex = r"^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}$"
        proto = data["protocol"]
        if proto == "EIGRP":
            if not data["proto_param"] or not data["proto_param"].isdigit():
                messagebox.showerror("Validation Error", "EIGRP AS Number parameter must be a numeric value.")
                return None
        elif proto == "OSPF":
            if not data["proto_param"]:
                messagebox.showerror("Validation Error", "OSPF Area ID must be completed.")
                return None
            is_ip = re.match(ip_regex, data["proto_param"])
            is_digit = data["proto_param"].isdigit()
            if not is_ip and not is_digit:
                messagebox.showerror("Validation Error", "OSPF Area ID must be either a numeric value or an IP address format (e.g. 0.0.0.104).")
                return None
        elif proto == "Static" or proto == "BGP":
            # No dynamic routing parameters checked
            pass

        # Nodes validation
        node_items = self.node_tree.get_children()
        if not node_items:
            messagebox.showerror("Validation Error", "Please configure at least one Leaf Node in the 'Leaf Nodes' tab.")
            return None

        cidr_regex = r"^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}/([1-2]?[0-9]|3[0-2])$"

        for item in node_items:
            values = self.node_tree.item(item, "values")
            pod, node_id, rtr_id = values[0], values[1], values[2]
            
            if not re.match(ip_regex, rtr_id):
                messagebox.showerror("Validation Error", f"Node {node_id}: Router IP '{rtr_id}' is not in a valid format.")
                return None

            data["nodes"].append({
                "pod": pod,
                "node_id": node_id,
                "router_id": rtr_id
            })

        # Interfaces validation
        if_items = self.if_tree.get_children()
        if not if_items:
            messagebox.showerror("Validation Error", "Please configure at least one Interface in the 'Interfaces' tab.")
            return None

        mac_regex = r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"

        for item in if_items:
            values = self.if_tree.item(item, "values")
            pod, node_id, port, ip_addr, if_type, vlan, mac = values[0], values[1], values[2], values[3], values[4], values[5], values[6]
            peer_ip, peer_asn, peer_ttl = values[7], values[8], values[9]
            
            if not re.match(cidr_regex, ip_addr):
                messagebox.showerror("Validation Error", f"Interface Node {node_id} Port {port}: IP '{ip_addr}' is not in a valid CIDR mask format (e.g. 10.1.1.1/30).")
                return None

            if if_type != "Routed":
                if not vlan.isdigit() or not (1 <= int(vlan) <= 4094):
                    messagebox.showerror("Validation Error", f"VLAN '{vlan}' must be a valid number between 1 and 4094 for Sub-Interface/SVI.")
                    return None

            if not re.match(mac_regex, mac):
                messagebox.showerror("Validation Error", f"MAC '{mac}' must be in standard hex format (e.g. 00:22:BD:F8:19:FF or 00-22-BD-F8-19-FF).")
                return None

            # BGP Peer parameters validation
            parsed_peer_ip = ""
            parsed_peer_asn = ""
            parsed_peer_ttl = ""
            if proto == "BGP":
                if not re.match(ip_regex, peer_ip):
                    messagebox.showerror("Validation Error", f"Interface Node {node_id} Port {port}: BGP Peer IP '{peer_ip}' is not in a valid IP format.")
                    return None
                if not peer_asn.isdigit():
                    messagebox.showerror("Validation Error", f"Interface Node {node_id} Port {port}: Remote BGP ASN '{peer_asn}' must be numeric.")
                    return None
                if not peer_ttl.isdigit() or not (1 <= int(peer_ttl) <= 255):
                    messagebox.showerror("Validation Error", f"Interface Node {node_id} Port {port}: TTL '{peer_ttl}' must be between 1 and 255.")
                    return None
                parsed_peer_ip = peer_ip
                parsed_peer_asn = peer_asn
                parsed_peer_ttl = peer_ttl

            # Clean port path to match ethX/Y if input as X/Y
            clean_port = port
            if not port.startswith("eth") and "/" in port:
                clean_port = "eth" + port

            data["interfaces"].append({
                "pod": pod,
                "node_id": node_id,
                "port": clean_port,
                "ip": ip_addr,
                "if_type": if_type,
                "vlan": vlan,
                "mac": mac,
                "peer_ip": parsed_peer_ip,
                "peer_asn": parsed_peer_asn,
                "peer_ttl": parsed_peer_ttl
            })

        return data

    def build_cobra_tree(self, data):
        """Constructs ACI Cobra Model Tree object using inputs."""
        if not COBRA_AVAILABLE:
            raise RuntimeError("Cisco ACI Cobra SDK is not loaded.")

        # Top level uni
        polUni = cobra.model.pol.Uni('')
        
        # Create/Reference L3 Domain (l3extDomP) under uni
        l3extDomP = cobra.model.l3ext.DomP(polUni, name=data["l3dom"])
        
        # Tenant
        fvTenant = cobra.model.fv.Tenant(polUni, data["tenant"])
        
        # L3Out
        l3extOut = cobra.model.l3ext.Out(
            fvTenant, 
            name=data["l3out"], 
            enforceRtctrl=u'export'
        )

        # Associate L3Out with L3Domain
        l3dom_dn = f"uni/l3dom-{data['l3dom']}"
        cobra.model.l3ext.RsL3DomAtt(l3extOut, tDn=l3dom_dn)

        # Associate L3Out with VRF (Ctx)
        cobra.model.l3ext.RsEctx(
            l3extOut, 
            tnFvCtxName=data["vrf"]
        )
        
        # Protocol-specific configuration
        proto = data["protocol"]
        if proto == "BGP":
            cobra.model.bgp.ExtP(
                l3extOut
            )
        elif proto == "OSPF":
            cobra.model.ospf.ExtP(
                l3extOut,
                areaCtrl=u'redistribute,summary',
                areaId=data["proto_param"],
                areaType=u'nssa',
                multipodInternal=u'no',
                areaCost=u'1'
            )
        elif proto == "EIGRP":
            cobra.model.eigrp.ExtP(
                l3extOut,
                asn=data["proto_param"]
            )
        # Static routing does not configure dynamic routing profile children

        # Node Profile (LNodeP)
        l3extLNodeP = cobra.model.l3ext.LNodeP(
            l3extOut, 
            name=data["node_profile"],
            tag=u'yellow-green'
        )
        
        # Interface Profile (LIfP)
        l3extLIfP = cobra.model.l3ext.LIfP(
            l3extLNodeP, 
            name=data["interface_profile"],
            tag=u'yellow-green'
        )

        # Add Interface Attachments (Paths)
        for item in data["interfaces"]:
            t_dn = f"topology/pod-{item['pod']}/paths-{item['node_id']}/pathep-[{item['port']}]"
            
            if_type = item.get("if_type", "Sub-Interface")
            if if_type == "Routed":
                if_inst_t = "l3-port"
                vlan_encap = "unknown"
            elif if_type == "SVI":
                if_inst_t = "ext-svi"
                vlan_encap = f"vlan-{item['vlan']}"
            else:
                if_inst_t = "sub-interface"
                vlan_encap = f"vlan-{item['vlan']}"

            l3path = cobra.model.l3ext.RsPathL3OutAtt(
                l3extLIfP,
                ipv6Dad=u'enabled',
                addr=item["ip"],
                encapScope=u'local',
                targetDscp=u'unspecified',
                llAddr=u'0.0.0.0',
                autostate=u'disabled',
                mac=item["mac"],
                mode=u'regular',
                encap=vlan_encap,
                ifInstT=if_inst_t,
                mtu=u'inherit',
                tDn=t_dn
            )

            # Link BGP Peer Connectivity Profile under RsPathL3OutAtt if protocol is BGP
            if proto == "BGP" and item["peer_ip"]:
                cobra.model.bgp.PeerP(
                    l3path,
                    addr=item["peer_ip"],
                    asn=item["peer_asn"],
                    ttl=item["peer_ttl"]
                )

        # Add Protocol-specific interface configuration
        if proto == "OSPF":
            ospfIfP = cobra.model.ospf.IfP(l3extLIfP, authType=u'none', name=u'OSPF', authKeyId=u'1')
            cobra.model.ospf.RsIfPol(ospfIfP, tnOspfIfPolName=u'default')

        # Add Node Attachments
        for node in data["nodes"]:
            t_dn = f"topology/pod-{node['pod']}/node-{node['node_id']}"
            
            l3extRsNodeL3OutAtt = cobra.model.l3ext.RsNodeL3OutAtt(
                l3extLNodeP, 
                tDn=t_dn, 
                rtrId=node["router_id"], 
                rtrIdLoopBack=u'yes'
            )
            cobra.model.l3ext.InfraNodeP(
                l3extRsNodeL3OutAtt, 
                spineRole=u'', 
                fabricExtIntersiteCtrlPeering=u'no', 
                fabricExtCtrlPeering=u'no'
            )

        return fvTenant, l3extDomP

    def generate_clean_json(self, data):
        """Generates a clean, pretty-printed Cisco ACI JSON REST payload structure."""
        l3out_children = []
        
        # 1. L3 Domain Association
        l3out_children.append({
            "l3extRsL3DomAtt": {
                "attributes": {
                    "tDn": f"uni/l3dom-{data['l3dom']}"
                }
            }
        })
        
        # 2. VRF Link
        l3out_children.append({
            "l3extRsEctx": {
                "attributes": {
                    "tnFvCtxName": data["vrf"],
                    "tDn": f"uni/tn-{data['tenant']}/ctx-{data['vrf']}",
                    "tRn": f"ctx-{data['vrf']}",
                    "rType": "mo",
                    "tCl": "fvCtx",
                    "forceResolve": "yes",
                    "userdom": "all"
                }
            }
        })
        
        # 3. Protocol configuration
        proto = data["protocol"]
        if proto == "BGP":
            l3out_children.append({
                "bgpExtP": {
                    "attributes": {
                        "name": "bgp",
                        "userdom": "all"
                    }
                }
            })
        elif proto == "OSPF":
            l3out_children.append({
                "ospfExtP": {
                    "attributes": {
                        "areaId": data["proto_param"],
                        "areaType": "nssa",
                        "areaCost": "1",
                        "multipodInternal": "no"
                    }
                }
            })
        elif proto == "EIGRP":
            l3out_children.append({
                "eigrpExtP": {
                    "attributes": {
                        "name": "eigrp",
                        "asn": data["proto_param"]
                    }
                }
            })
        # Static Routing has no routing protocol profile elements

        # 4. Node Profile (LNodeP)
        node_children = []
        
        # Add Logical Nodes
        for node in data["nodes"]:
            node_children.append({
                "l3extRsNodeL3OutAtt": {
                    "attributes": {
                        "tDn": f"topology/pod-{node['pod']}/node-{node['node_id']}",
                        "rtrId": node["router_id"],
                        "rtrIdLoopBack": "yes"
                    },
                    "children": [
                        {
                            "l3extInfraNodeP": {
                                "attributes": {
                                    "fabricExtCtrlPeering": "no",
                                    "fabricExtIntersiteCtrlPeering": "no"
                                }
                            }
                        }
                    ]
                }
            })
            
        # Interface Profile (LIfP)
        if_children = []
        
        # Add Path Attachments
        for item in data["interfaces"]:
            if_type = item.get("if_type", "Sub-Interface")
            if if_type == "Routed":
                if_inst_t = "l3-port"
                encap_val = "unknown"
            elif if_type == "SVI":
                if_inst_t = "ext-svi"
                encap_val = f"vlan-{item['vlan']}"
            else:
                if_inst_t = "sub-interface"
                encap_val = f"vlan-{item['vlan']}"

            path_attrs = {
                "tDn": f"topology/pod-{item['pod']}/paths-{item['node_id']}/pathep-[{item['port']}]",
                "addr": item["ip"],
                "encap": encap_val,
                "mac": item["mac"],
                "mode": "regular",
                "ifInstT": if_inst_t,
                "autostate": "disabled",
                "mtu": "inherit"
            }
            
            path_children = []
            if proto == "BGP" and item["peer_ip"]:
                path_children.append({
                    "bgpPeerP": {
                        "attributes": {
                            "addr": item["peer_ip"],
                            "asn": item["peer_asn"],
                            "ttl": item["peer_ttl"]
                        }
                    }
                })
                
            if path_children:
                if_children.append({
                    "l3extRsPathL3OutAtt": {
                        "attributes": path_attrs,
                        "children": path_children
                    }
                })
            else:
                if_children.append({
                    "l3extRsPathL3OutAtt": {
                        "attributes": path_attrs
                    }
                })
                
        # OSPF Interface config
        if proto == "OSPF":
            if_children.append({
                "ospfIfP": {
                    "attributes": {
                        "name": "OSPF",
                        "authType": "none",
                        "authKeyId": "1"
                    },
                    "children": [
                        {
                            "ospfRsIfPol": {
                                "attributes": {
                                    "tnOspfIfPolName": "default"
                                }
                            }
                        }
                    ]
                }
            })
            
        # Add Interface Profile to Node Profile children
        node_children.append({
            "l3extLIfP": {
                "attributes": {
                    "name": data["interface_profile"],
                    "tag": "yellow-green"
                },
                "children": if_children
            }
        })
        
        # Add Node Profile to L3Out children
        l3out_children.append({
            "l3extLNodeP": {
                "attributes": {
                    "name": data["node_profile"],
                    "tag": "yellow-green"
                },
                "children": node_children
            }
        })
        
        # Combine into complete ACI REST Payload under polUni root
        payload = {
            "polUni": {
                "attributes": {},
                "children": [
                    {
                        "fvTenant": {
                            "attributes": {
                                "name": data["tenant"]
                            },
                            "children": [
                                {
                                    "l3extOut": {
                                        "attributes": {
                                            "name": data["l3out"],
                                            "mplsEnabled": "no",
                                            "targetDscp": "unspecified",
                                            "enforceRtctrl": "export",
                                            "userdom": "all"
                                        },
                                        "children": l3out_children
                                    }
                                }
                            ]
                        }
                    },
                    {
                        "l3extDomP": {
                            "attributes": {
                                "name": data["l3dom"]
                            }
                        }
                    }
                ]
            }
        }
        
        return json.dumps(payload, indent=2)

    def action_validate(self):
        self.notebook.select(self.tab_console)  # Switch tab to console
        data = self.get_and_validate_inputs()
        if data:
            self.log(f"Validation Successful! Inputs for {data['protocol']} conform to schema.")
            messagebox.showinfo("Success", "All inputs validated successfully!")

    def action_preview(self):
        self.notebook.select(self.tab_console)  # Switch tab to console
        data = self.get_and_validate_inputs()
        if not data:
            return

        self.log(f"Generating Clean JSON preview for {data['protocol']}...")
        try:
            json_content = self.generate_clean_json(data)
            self.show_json_viewer(f"Clean ACI JSON Payload ({data['protocol']} Routing)", json_content)
            self.log("Clean JSON payload preview generated successfully.")
        except Exception as e:
            self.log(f"Error building JSON payload: {str(e)}")
            messagebox.showerror("Error", f"Failed to generate JSON payload: {str(e)}")

    def show_json_viewer(self, title, content):
        """Displays JSON in a new popup window with copy-to-clipboard option."""
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("700x550")
        
        frame = ttk.Frame(win, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        txt = scrolledtext.ScrolledText(frame, font=("Consolas", 10))
        txt.insert(tk.END, content)
        txt.configure(state=tk.DISABLED)
        txt.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        btn_box = ttk.Frame(frame)
        btn_box.pack(fill=tk.X)

        def copy_clip():
            win.clipboard_clear()
            win.clipboard_append(content)
            messagebox.showinfo("Copied", "Copied to clipboard!", parent=win)

        ttk.Button(btn_box, text="Copy to Clipboard", command=copy_clip).pack(side=tk.LEFT)
        ttk.Button(btn_box, text="Close", command=win.destroy).pack(side=tk.RIGHT)

    def action_push(self):
        self.notebook.select(self.tab_console)  # Switch tab to console
        data = self.get_and_validate_inputs()
        if not data:
            return

        confirm = messagebox.askyesno("Confirm Action", f"Are you sure you want to push this {data['protocol']} configuration to the ACI fabric?")
        if not confirm:
            return

        self.log(f"Starting {data['protocol']} push thread...")
        thread = threading.Thread(target=self.push_process, args=(data,))
        thread.daemon = True
        thread.start()

    def push_process(self, data):
        if not COBRA_AVAILABLE:
            self.log("[SIMULATION] Connecting to APIC at " + data["apic_url"] + " ...")
            self.log("[SIMULATION] Logged in as: " + data["username"])
            self.log(f"[SIMULATION] Checking Tenant '{data['tenant']}' existence on APIC...")
            self.log(f"[SIMULATION] Checking VRF '{data['vrf']}' existence on APIC...")
            self.log(f"[SIMULATION] Checking if L3Out '{data['l3out']}' exists...")
            self.log(f"[SIMULATION] Committing {data['protocol']} configuration tree to ACI...")
            self.log("[SIMULATION] Configuration mock push completed successfully!")
            self.after(0, lambda: messagebox.showinfo("Mock Success", "Simulation Mode: Configuration simulated successfully!"))
            return

        self.log(f"Connecting to APIC: {data['apic_url']} ...")
        try:
            ls = cobra.mit.session.LoginSession(data["apic_url"], data["username"], data["password"])
            md = cobra.mit.access.MoDirectory(ls)
            md.login()
            self.log("Authenticated successfully with APIC.")

            # Safety Checks: verify Tenant, VRF existence, and warn if L3Out already exists
            self.log("Performing ACI object safety checks...")
            tenant_dn = f"uni/tn-{data['tenant']}"
            vrf_dn = f"uni/tn-{data['tenant']}/ctx-{data['vrf']}"
            l3out_dn = f"uni/tn-{data['tenant']}/out-{data['l3out']}"

            # 1. Tenant Check
            tenant_mo = md.lookupByDn(tenant_dn)
            if not tenant_mo:
                self.log(f"ERROR: Tenant '{data['tenant']}' does not exist on the APIC.")
                self.after(0, lambda: messagebox.showerror("Push Cancelled", f"Tenant '{data['tenant']}' does not exist on the APIC.\nPlease create the Tenant on the APIC first."))
                return

            # 2. VRF Check
            vrf_mo = md.lookupByDn(vrf_dn)
            if not vrf_mo:
                self.log(f"ERROR: VRF '{data['vrf']}' does not exist under Tenant '{data['tenant']}' on the APIC.")
                self.after(0, lambda: messagebox.showerror("Push Cancelled", f"VRF '{data['vrf']}' does not exist under Tenant '{data['tenant']}' on the APIC.\nPlease create the VRF on the APIC first."))
                return

            # 3. L3Out Check
            l3out_mo = md.lookupByDn(l3out_dn)
            if l3out_mo:
                self.log(f"Notice: L3Out '{data['l3out']}' already exists on the APIC.")
                import queue
                q = queue.Queue()
                def ask_confirm(q_obj):
                    ans = messagebox.askyesno(
                        "L3Out Already Exists",
                        f"L3Out '{data['l3out']}' already exists in Tenant '{data['tenant']}'.\n\n"
                        "Pushing this configuration will merge/update the node profiles and interfaces.\n"
                        "It will NOT delete any other existing configuration on the APIC.\n\n"
                        "Do you want to proceed?",
                        parent=self
                    )
                    q_obj.put(ans)
                self.after(0, lambda: ask_confirm(q))
                proceed = q.get()
                if not proceed:
                    self.log("Push cancelled by user (L3Out already exists).")
                    return

            fv_tenant_obj, l3ext_dom_obj = self.build_cobra_tree(data)
            self.log(f"Cobra Model object tree for {data['protocol']} built successfully.")

            config_req = cobra.mit.request.ConfigRequest()
            config_req.addMo(fv_tenant_obj)
            config_req.addMo(l3ext_dom_obj)
            self.log("Committing changes to APIC...")
            md.commit(config_req)
            self.log("Transaction successfully committed to ACI fabric!")
            
            self.after(0, lambda: messagebox.showinfo("Success", f"{data['protocol']} ACI configuration pushed successfully!"))

        except Exception as e:
            self.log(f"ERROR: Configuration push failed: {str(e)}")
            self.after(0, lambda: messagebox.showerror("Push Error", f"Configuration push failed:\n{str(e)}"))

if __name__ == "__main__":
    app = BGP_L3OutApp()
    app.mainloop()
