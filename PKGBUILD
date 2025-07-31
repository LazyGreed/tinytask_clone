# Maintainer: LazyGreed <kosalseng.lazygreed@proton.me>

pkgname=tinytask-enhanced
pkgver=0.1.0
pkgrel=1
pkgdesc="TinyTask for Linux - Enhanced GUI macro recorder/player"
arch=('any')
url="https://github.com/yourusername/tinytask-enhanced"
license=('MIT')
depends=('python' 'python-pynput' 'python-pyqt5')
source=("tinytask_enhanced.py" "tinytask-enhanced.desktop")
md5sums=('SKIP' 'SKIP')

package() {
    install -Dm755 "$srcdir/tinytask_enhanced.py" "$pkgdir/usr/bin/tinytask-enhanced"
    install -Dm644 "$srcdir/tinytask-enhanced.desktop" "$pkgdir/usr/share/applications/tinytask-enhanced.desktop"
}
