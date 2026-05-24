import wx
import ast
import operator
from api import BlindApp

class Calculator(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "Calculator"
        self.description = "Perform mathematical calculations."
        self.help_text = "Type an expression or use the number pad. Enter to calculate, Up/Down for history."
        self.docs = "Supports +, -, *, /, //, %, **. Click memory buttons to store/recall/clear."
        self.history = []
        self.history_idx = -1
        self.memory = None

    def run(self):
        # Register accelerators for number/operator keys
        nid = 1000
        for d in "0123456789":
            self.bind_accelerator(wx.ACCEL_NORMAL, ord(d), nid, lambda evt, x=d: self.on_insert(x))
            nid += 1
        for d in "+-*/.":
            self.bind_accelerator(wx.ACCEL_NORMAL, ord(d), nid, lambda evt, x=d: self.on_insert(x))
            nid += 1
        self.bind_accelerator(wx.ACCEL_NORMAL, wx.WXK_RETURN, nid, self.on_calculate); nid += 1
        self.bind_accelerator(wx.ACCEL_NORMAL, wx.WXK_ESCAPE, nid, self.on_clear)

        self._create_frame("Calculator", (320, 480))
        panel = self.make_panel(self.frame, "Calculator Panel")
        sizer = self.vbox()

        self.display = self.make_textctrl(panel, name="Calculator Display", style=wx.TE_PROCESS_ENTER)
        self.display.SetBackgroundColour(wx.Colour(30, 30, 30))
        self.display.SetForegroundColour(wx.Colour(255, 255, 255))
        self.display.SetFont(wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.display.Bind(wx.EVT_TEXT_ENTER, self.on_calculate)
        self.display.Bind(wx.EVT_KEY_DOWN, self.on_key)
        sizer.Add(self.display, 0, wx.EXPAND | wx.ALL, 10)

        self.result_label = wx.StaticText(panel, label="Result: ", style=wx.ALIGN_RIGHT)
        self.result_label.SetName("Calculator Result")
        self.result_label.SetForegroundColour(wx.Colour(100, 255, 100))
        self.result_label.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(self.result_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        num_pad = wx.GridSizer(5, 4, 3, 3)
        buttons = [
            ("7", "7"), ("8", "8"), ("9", "9"), ("/", "/"),
            ("4", "4"), ("5", "5"), ("6", "6"), ("*", "*"),
            ("1", "1"), ("2", "2"), ("3", "3"), ("-", "-"),
            ("0", "0"), (".", "."), ("C", "C"), ("+", "+"),
            ("MC", "MC"), ("MR", "MR"), ("M+", "M+"), ("=", "="),
        ]
        def make_handler(a):
            if a == "=":
                return self.on_calculate
            if a == "C":
                return self.on_clear
            if a == "MC":
                return lambda evt: self.on_memory("MC")
            if a == "MR":
                return lambda evt: self.on_memory("MR")
            if a == "M+":
                return lambda evt: self.on_memory("M+")
            return lambda evt, d=a: self.on_insert(d)
        for label, action in buttons:
            btn = self.make_button(panel, label, make_handler(action), label)
            btn.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            num_pad.Add(btn, 0, wx.EXPAND)
        sizer.Add(num_pad, 0, wx.EXPAND | wx.ALL, 10)

        self.history_box = self.make_listbox(panel, name="History")
        self.history_box.SetBackgroundColour(wx.Colour(20, 20, 20))
        self.history_box.SetForegroundColour(wx.Colour(200, 200, 200))
        self.history_box.Bind(wx.EVT_LISTBOX_DCLICK, self.on_history_select)
        sizer.Add(self.history_box, 1, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(sizer)
        self.api.speak("Calculator opened.")
        self._show_app(self.display)

    def on_insert(self, text):
        self.display.AppendText(text)
        self.display.SetFocus()

    def on_key(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_UP:
            self.navigate_history(1)
        elif key == wx.WXK_DOWN:
            self.navigate_history(-1)
        else:
            event.Skip()

    def navigate_history(self, direction):
        if not self.history: return
        self.history_idx = max(0, min(len(self.history)-1, self.history_idx + direction))
        self.display.SetValue(self.history[self.history_idx])

    def on_clear(self, event=None):
        self.display.Clear()
        self.result_label.SetLabel("Result: ")
        self.display.SetFocus()

    def on_history_select(self, event):
        sel = self.history_box.GetSelection()
        if sel != wx.NOT_FOUND:
            self.display.SetValue(self.history[sel])
            self.display.SetFocus()

    def on_memory(self, action):
        if action == "MC":
            self.memory = None
            self.api.speak("Memory cleared.")
        elif action == "MR":
            if self.memory is not None:
                self.display.SetValue(str(self.memory))
                self.display.SetFocus()
                self.api.speak(f"Recalled {self.memory}")
            else:
                self.api.speak("Memory is empty.")
        elif action == "M+":
            expr = self.display.GetValue()
            if expr:
                try:
                    val = self._safe_eval(expr)
                    self.memory = val
                    self.api.speak(f"Stored {val} in memory.")
                except Exception:
                    self.api.speak("Invalid expression.")
            else:
                self.api.speak("Nothing to store.")

    def on_calculate(self, event):
        expr = self.display.GetValue()
        if not expr:
            return
        try:
            res = self._safe_eval(expr)
            self.result_label.SetLabel(f"Result: {res}")
            self.history.append(expr)
            self.history_idx = len(self.history) - 1
            self.history_box.Append(f"{expr} = {res}")
            self.display.Clear()
            self.display.SetFocus()
            self.api.speak(f"The result is {res}")
        except SyntaxError:
            self.api.speak("Invalid syntax.")
        except ZeroDivisionError:
            self.api.speak("Cannot divide by zero.")
        except Exception:
            self.api.speak("Invalid expression.")

    def _safe_eval(self, expr):
        allowed_ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.FloorDiv: operator.floordiv,
            ast.Pow: operator.pow,
            ast.Mod: operator.mod,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }
        node = ast.parse(expr.strip(), mode="eval").body

        def _eval(n):
            if isinstance(n, ast.Expression):
                return _eval(n.body)
            if isinstance(n, ast.Constant):
                return n.value
            if isinstance(n, ast.BinOp):
                op = allowed_ops.get(type(n.op))
                if op is None:
                    raise ValueError("Unsupported operator")
                return op(_eval(n.left), _eval(n.right))
            if isinstance(n, ast.UnaryOp):
                op = allowed_ops.get(type(n.op))
                if op is None:
                    raise ValueError("Unsupported operator")
                return op(_eval(n.operand))
            raise ValueError("Unsupported expression")

        result = _eval(node)
        if isinstance(result, float) and result == int(result):
            result = int(result)
        return result


