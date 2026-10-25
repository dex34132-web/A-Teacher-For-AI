class Toolio < Formula
  desc "Universal agent learning and memory system"
  homepage "https://github.com/dex34132-web/toolio"
  url "https://github.com/dex34132-web/toolio/archive/refs/tags/v2.6.0.tar.gz"
  # sha256: compute with: shasum -a 256 v2.6.0.tar.gz
  # or: curl -sL https://github.com/dex34132-web/toolio/archive/refs/tags/v2.6.0.tar.gz | shasum -a 256
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  def post_install
    system "#{bin}/toolio", "install"
  end

  test do
    assert_match "toolio #{version}", shell_output("#{bin}/toolio version")
  end
end
