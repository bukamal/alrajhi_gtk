# -*- coding: utf-8 -*-
"""
"""

import os
import sys
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

class PrinterType(Enum):
    USB = "usb"
    SERIAL = "serial"
    NETWORK = "network"
    PDF = "pdf"
    IMAGE = "image"

@dataclass
class PrinterInfo:
    """معلومات الطابعة"""
    id: str
    name: str
    type: PrinterType
    connection_string: str
    is_default: bool = False
    capabilities: List[str] = None

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []


class PrinterManager:
    """كشف وإدارة الطابعات المتاحة"""
    
    def __init__(self):
        self.printers: List[PrinterInfo] = []
        self._detect_printers()
    
    def _detect_printers(self):
        """كشف الطابعات المتاحة في النظام"""
        self.printers.clear()
        
        # 1. كشف الطابعات التسلسلية (USB-to-Serial)
        try:
            import serial.tools.list_ports
            for port in serial.tools.list_ports.comports():
                if any(keyword in port.description.lower() for keyword in ['printer', 'thermal', 'pos', 'epson', 'citizen']):
                    self.printers.append(PrinterInfo(
                        id=f"serial:{port.device}",
                        name=f"{port.description} ({port.device})",
                        type=PrinterType.SERIAL,
                        connection_string=port.device
                    ))
        except ImportError:
            pass
        
        # 2. كشف طابعات USB المباشرة (Linux)
        if sys.platform.startswith('linux'):
            for i in range(4):
                dev = f"/dev/usb/lp{i}"
                if os.path.exists(dev):
                    self.printers.append(PrinterInfo(
                        id=f"usb:{dev}",
                        name=f"طابعة USB مباشرة ({dev})",
                        type=PrinterType.USB,
                        connection_string=dev
                    ))
        
        # 3. إضافة طابعة PDF افتراضية
        self.printers.append(PrinterInfo(
            id="pdf:default",
            name="حفظ كـ PDF",
            type=PrinterType.PDF,
            connection_string=""
        ))
        
        # 4. إضافة طابعة صورة PNG
        self.printers.append(PrinterInfo(
            id="image:png",
            name="حفظ كـ صورة PNG",
            type=PrinterType.IMAGE,
            connection_string=""
        ))
    
    def get_default_printer(self) -> Optional[PrinterInfo]:
        for p in self.printers:
            if p.is_default:
                return p
        return self.printers[0] if self.printers else None
    
    def get_printer(self, printer_id: str) -> Optional[PrinterInfo]:
        for p in self.printers:
            if p.id == printer_id:
                return p
        return None
    
    def add_network_printer(self, host: str, port: int = 9100, name: str = None):
        printer_id = f"network:{host}:{port}"
        if not self.get_printer(printer_id):
            self.printers.append(PrinterInfo(
                id=printer_id,
                name=name or f"طابعة شبكية {host}:{port}",
                type=PrinterType.NETWORK,
                connection_string=f"{host}:{port}"
            ))
    
    def save_default_printer(self, printer_id: str):
        for p in self.printers:
            p.is_default = (p.id == printer_id)
        from PyQt5.QtCore import QSettings
        settings = QSettings("Alrajhi", "Accounting")
        settings.setValue("printer/default", printer_id)
    
    def load_default_printer(self):
        from PyQt5.QtCore import QSettings
        settings = QSettings("Alrajhi", "Accounting")
        printer_id = settings.value("printer/default", "")
        if printer_id:
            for p in self.printers:
                p.is_default = (p.id == printer_id)
