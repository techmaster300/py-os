import unittest
import os
import shutil
from kernel import VirtualOS

class TestKernel(unittest.TestCase):
    def setUp(self):
        self.root = "test_vfs"
        if os.path.exists(self.root):
            shutil.rmtree(self.root)
        self.os = VirtualOS(root_dir=self.root)

    def tearDown(self):
        if os.path.exists(self.root):
            shutil.rmtree(self.root)

    def test_path_traversal(self):
        # Attempt to access a file outside the root_dir
        traversal_path = "../../"
        real_path = self.os.get_real_path(traversal_path)
        
        # The real_path should still be within self.root
        abs_root = os.path.abspath(self.root)
        abs_real_path = os.path.abspath(real_path)
        
        self.assertTrue(abs_real_path.startswith(abs_root), f"Path traversal detected: {abs_real_path} is outside {abs_root}")

    def test_list_command(self):
        response = self.os.execute("list")
        self.assertIn("welcome.txt", response)
        self.assertIn("documents", response)

if __name__ == "__main__":
    unittest.main()
