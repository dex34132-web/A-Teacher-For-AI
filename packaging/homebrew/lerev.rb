class Lerev < Formula
  desc "Universal agent learning and memory system"
  homepage "https://github.com/dkshs/lerev"
  url "https://github.com/dkshs/lerev/archive/refs/tags/v2.6.0.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  def post_install
    system "#{bin}/lerev", "install"
  end

  test do
    assert_match "lerev #{version}", shell_output("#{bin}/lerev version")
  end
end
