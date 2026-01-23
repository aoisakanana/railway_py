"""Hello World entry point - セットアップ確認用."""

from railway import entry_point


@entry_point
def hello():
    """最小限のHello World

    railway init 後すぐに動作確認できます:
        uv run railway run hello
    """
    print("Hello, World!")
    return {"message": "Hello, World!"}


if __name__ == "__main__":
    hello()
